"""
test_synthetic_data.py — Validation and Testing Script for Synthetic Contract Data

This script validates the synthetic contracts.json file and runs test scenarios
to ensure the data is properly structured and suitable for testing all BigBurger
AI features.

Usage:
    cd prototype
    python test_synthetic_data.py

    # Or with specific test mode:
    python test_synthetic_data.py --mode validate
    python test_synthetic_data.py --mode load
    python test_synthetic_data.py --mode scenarios
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import REGIONS, ROLE_PERMISSIONS, MOCK_USERS
from ingestion.pipeline import load_documents, run_ingestion_pipeline
from retrieval.vector_store import MultiTenantVectorStore
from agents.orchestrator_agent import OrchestratorAgent
from retrieval.retriever import MultiTenantRetriever


class SyntheticDataValidator:
    """Validates synthetic contract data structure and completeness."""
    
    REQUIRED_FIELDS = {
        "doc_id", "region", "subsidiary", "doc_type", "title", 
        "content", "effective_date", "expiry_date", "liability_amount", 
        "currency", "tags", "last_modified", "version"
    }
    
    REQUIRED_SUPPLIER_FIELDS = {
        "vendor_contract": {"supplier"},
        "lease_agreement": {"landlord"},
        "compliance": {"issuer"},
    }
    
    VALID_DOC_TYPES = {"vendor_contract", "lease_agreement", "compliance"}
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}
    
    def validate_file(self, path: Path) -> bool:
        """Validate the synthetic data file."""
        print(f"\n{'='*70}")
        print("VALIDATION: Synthetic Contracts File")
        print(f"{'='*70}\n")
        
        try:
            documents = load_documents(path)
        except Exception as e:
            self.errors.append(f"Failed to load file: {e}")
            return False
        
        print(f"✓ File loaded successfully: {len(documents)} documents\n")
        
        # Validate individual documents
        for i, doc in enumerate(documents, 1):
            self._validate_document(doc, i)
        
        # Validate dataset completeness
        self._validate_dataset_stats(documents)
        
        return self._print_results()
    
    def _validate_document(self, doc: Dict[str, Any], index: int) -> None:
        """Validate a single document."""
        doc_id = doc.get("doc_id", f"<missing at index {index}>")
        
        # Check required fields
        missing = self.REQUIRED_FIELDS - set(doc.keys())
        if missing:
            self.errors.append(f"{doc_id}: Missing fields: {missing}")
        
        # Check doc_type
        doc_type = doc.get("doc_type")
        if doc_type not in self.VALID_DOC_TYPES:
            self.errors.append(f"{doc_id}: Invalid doc_type '{doc_type}'")
        else:
            # Check supplier/landlord/issuer based on type
            required_supplier = self.REQUIRED_SUPPLIER_FIELDS.get(doc_type, set())
            if required_supplier:
                supplied_fields = [f for f in required_supplier if f in doc and doc[f]]
                if not supplied_fields:
                    self.errors.append(f"{doc_id}: Missing {required_supplier} for {doc_type}")
        
        # Check region
        region = doc.get("region")
        if region not in REGIONS + ["corporate"]:
            self.errors.append(f"{doc_id}: Invalid region '{region}'")
        
        # Validate dates
        try:
            eff_date = datetime.fromisoformat(doc.get("effective_date", ""))
            exp_date = datetime.fromisoformat(doc.get("expiry_date", ""))
            if exp_date < eff_date:
                self.errors.append(f"{doc_id}: Expiry date before effective date")
        except (ValueError, TypeError) as e:
            self.errors.append(f"{doc_id}: Invalid date format")
        
        # Check liability amount
        liability = doc.get("liability_amount")
        if not isinstance(liability, (int, float)) or liability < 0:
            self.errors.append(f"{doc_id}: Invalid liability_amount")
        
        # Check content length
        content = doc.get("content", "")
        if len(content) < 100:
            self.warnings.append(f"{doc_id}: Content very short ({len(content)} chars)")
        
        # Check tags
        tags = doc.get("tags", [])
        if not isinstance(tags, list) or not tags:
            self.warnings.append(f"{doc_id}: Missing or empty tags")
    
    def _validate_dataset_stats(self, documents: List[Dict]) -> None:
        """Validate dataset statistics and coverage."""
        by_region = defaultdict(list)
        by_type = defaultdict(list)
        liabilities = []
        
        for doc in documents:
            region = doc.get("region")
            doc_type = doc.get("doc_type")
            liability = doc.get("liability_amount", 0)
            
            by_region[region].append(doc)
            by_type[doc_type].append(doc)
            liabilities.append(liability)
        
        self.stats = {
            "total_documents": len(documents),
            "by_region": {r: len(docs) for r, docs in by_region.items()},
            "by_type": {t: len(docs) for t, docs in by_type.items()},
            "total_liability": sum(liabilities),
            "max_liability": max(liabilities),
            "avg_liability": sum(liabilities) / len(liabilities) if liabilities else 0,
        }
    
    def _print_results(self) -> bool:
        """Print validation results."""
        print(f"\n{'─'*70}")
        print("STATISTICS")
        print(f"{'─'*70}")
        for key, value in self.stats.items():
            if isinstance(value, dict):
                print(f"\n{key.upper().replace('_', ' ')}:")
                for k, v in value.items():
                    print(f"  {k:20s}: {v}")
            else:
                print(f"{key.replace('_', ' ').title():20s}: {value:,.0f}")
        
        print(f"\n{'─'*70}")
        print("VALIDATION SUMMARY")
        print(f"{'─'*70}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors:
            print("\n✅ All validation checks passed!")
            return True
        else:
            print(f"\n❌ Validation failed with {len(self.errors)} error(s)")
            return False


class TestScenarioRunner:
    """Runs test scenarios using the synthetic data."""
    
    def __init__(self, orchestrator: OrchestratorAgent):
        self.orchestrator = orchestrator
        self.results = []
    
    def run_all_scenarios(self) -> None:
        """Run all predefined test scenarios."""
        print(f"\n{'='*70}")
        print("TEST SCENARIOS: Running Orchestrator Tests")
        print(f"{'='*70}\n")
        
        scenarios = [
            {
                "name": "Local Regional Query",
                "user_id": "alice_north",
                "query": "When does our beef supplier contract expire?",
                "expected_type": "local",
            },
            {
                "name": "Global Auditor - Cross-Regional Conflict",
                "user_id": "eve_auditor",
                "query": "Which regional subsidiaries have FizzCo exclusivity clauses?",
                "expected_type": "cross_regional",
            },
            {
                "name": "RBAC Test - Regional Manager Cross-Region Attempt",
                "user_id": "bob_south",
                "query": "Show me all beverage contracts across all regions",
                "expected_type": "local_blocked",
            },
            {
                "name": "Authentication Test - Invalid User",
                "user_id": "hacker_unknown",
                "query": "Show me all contracts",
                "expected_type": "auth_error",
            },
            {
                "name": "HQ Executive - Aggregation Query",
                "user_id": "frank_hq",
                "query": "What is our total liability across all lease agreements?",
                "expected_type": "cross_regional",
            },
            {
                "name": "Compliance Deadline Tracking",
                "user_id": "frank_hq",
                "query": "What compliance certifications and permits expire soon?",
                "expected_type": "cross_regional",
            },
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n[SCENARIO {i}/{len(scenarios)}] {scenario['name']}")
            print(f"{'─'*70}")
            
            try:
                response = self.orchestrator.handle_query(
                    user_id=scenario['user_id'],
                    query_text=scenario['query'],
                )
                
                self._print_response(response)
                
                # Log result
                self.results.append({
                    "scenario": scenario['name'],
                    "status": "pass" if not response.get("error") else "fail",
                    "user": scenario['user_id'],
                    "regions_queried": response.get("regions_queried", []),
                })
            except Exception as e:
                print(f"❌ Exception: {e}")
                self.results.append({
                    "scenario": scenario['name'],
                    "status": "error",
                    "error": str(e),
                })
    
    def _print_response(self, response: Dict[str, Any]) -> None:
        """Pretty-print an orchestrator response."""
        print(f"User:         {response['user']} (role: {response['role']})")
        print(f"Query Type:   {response['query_type'].upper()}")
        print(f"Regions:      {', '.join(response.get('regions_queried', [])) or 'none'}")
        
        if response.get("error"):
            print(f"\n⛔ Error: {response['error']}")
        else:
            answer_preview = response['answer'][:200] + "..." if len(response['answer']) > 200 else response['answer']
            print(f"\nAnswer (preview):\n{answer_preview}")
    
    def print_summary(self) -> None:
        """Print test summary."""
        print(f"\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}\n")
        
        passed = sum(1 for r in self.results if r['status'] == 'pass')
        failed = sum(1 for r in self.results if r['status'] == 'fail')
        errors = sum(1 for r in self.results if r['status'] == 'error')
        
        print(f"Total Scenarios: {len(self.results)}")
        print(f"✅ Passed:      {passed}")
        print(f"❌ Failed:      {failed}")
        print(f"⚠️  Errors:      {errors}")
        
        if failed + errors == 0:
            print(f"\n🎉 All scenarios passed!")
        else:
            print(f"\n⚠️  {failed + errors} scenario(s) did not pass")


def main():
    parser = argparse.ArgumentParser(
        description="Validate and test synthetic contract data for BigBurger AI"
    )
    parser.add_argument(
        "--mode",
        choices=["validate", "load", "scenarios", "all"],
        default="all",
        help="Test mode to run"
    )
    parser.add_argument(
        "--file",
        default="mock_data/synthetic_contracts.json",
        help="Path to synthetic contracts file"
    )
    
    args = parser.parse_args()
    
    file_path = Path(__file__).parent / args.file
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    # Mode: Validate
    if args.mode in ["validate", "all"]:
        validator = SyntheticDataValidator()
        valid = validator.validate_file(file_path)
        if args.mode == "validate":
            sys.exit(0 if valid else 1)
    
    # Mode: Load
    if args.mode in ["load", "all"]:
        print(f"\n{'='*70}")
        print("LOADING DATA: Building Vector Store and Ingesting Contracts")
        print(f"{'='*70}\n")
        
        try:
            store = MultiTenantVectorStore()
            chunk_count = run_ingestion_pipeline(store, verbose=True)
            print(f"✅ Successfully loaded {chunk_count} chunks from contracts")
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
            sys.exit(1)
        
        if args.mode == "load":
            sys.exit(0)
    
    # Mode: Scenarios
    if args.mode in ["scenarios", "all"]:
        try:
            store = MultiTenantVectorStore()
            run_ingestion_pipeline(store, verbose=False)
            
            retriever = MultiTenantRetriever(store)
            orchestrator = OrchestratorAgent(retriever)
            
            runner = TestScenarioRunner(orchestrator)
            runner.run_all_scenarios()
            runner.print_summary()
        except Exception as e:
            print(f"❌ Failed to run scenarios: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
