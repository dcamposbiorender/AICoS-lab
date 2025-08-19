#!/usr/bin/env python3
"""
Advanced Performance Testing Suite

Tests performance bottlenecks, query optimization opportunities,
and realistic concurrent load scenarios.
"""

import sys
import time
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import random
import string

def profile_database_queries() -> Dict[str, Any]:
    """Profile database query execution plans and identify optimization opportunities."""
    print("🔍 Profiling Database Query Execution")
    print("-" * 50)
    
    conn = sqlite3.connect('search.db')
    cursor = conn.cursor()
    
    # Enable query plan analysis
    cursor.execute("ANALYZE")
    
    test_queries = [
        ("Simple match", "SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'test'"),
        ("Complex AND", "SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'project AND meeting'"),
        ("Phrase search", "SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH '\"all hands meeting\"'"),
        ("Date filter", "SELECT COUNT(*) FROM messages WHERE date = '2025-08-16'"),
        ("Source filter", "SELECT COUNT(*) FROM messages WHERE source = 'slack'"),
        ("Combined filter", "SELECT COUNT(*) FROM messages m JOIN messages_fts f ON m.rowid = f.rowid WHERE f.messages_fts MATCH 'company' AND m.source = 'slack'"),
    ]
    
    query_profiles = []
    
    for query_name, query in test_queries:
        print(f"  📊 Profiling: {query_name}")
        
        # Get query plan
        explain_query = f"EXPLAIN QUERY PLAN {query}"
        cursor.execute(explain_query)
        query_plan = cursor.fetchall()
        
        # Measure execution time (multiple runs for average)
        times = []
        for _ in range(5):
            start_time = time.perf_counter()
            cursor.execute(query)
            result = cursor.fetchone()[0]
            execution_time = time.perf_counter() - start_time
            times.append(execution_time)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        query_profiles.append({
            "name": query_name,
            "query": query,
            "execution_plan": [{"step": plan[1], "table": plan[2], "detail": plan[3]} for plan in query_plan],
            "avg_time_ms": avg_time * 1000,
            "min_time_ms": min_time * 1000,
            "max_time_ms": max_time * 1000,
            "result_count": result
        })
        
        print(f"    ⏱️  Avg: {avg_time*1000:.2f}ms, Min: {min_time*1000:.2f}ms, Max: {max_time*1000:.2f}ms")
        print(f"    📊 Results: {result:,}")
    
    # Identify slow queries
    slow_queries = [q for q in query_profiles if q["avg_time_ms"] > 50]  # >50ms considered slow
    
    # Check for missing indexes
    cursor.execute("PRAGMA index_list(messages)")
    indexes = cursor.fetchall()
    
    # Database statistics
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages_fts")
    fts_messages = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_messages": total_messages,
        "fts_messages": fts_messages,
        "query_profiles": query_profiles,
        "slow_queries": len(slow_queries),
        "existing_indexes": len(indexes),
        "optimization_opportunities": [
            "Consider adding index on date column" if any("date" in q["query"] for q in slow_queries) else None,
            "Consider adding index on source column" if any("source" in q["query"] for q in slow_queries) else None,
            "FTS rebuild might help" if fts_messages < total_messages * 0.9 else None
        ]
    }

def load_test_concurrent_users(num_users: int = 50, queries_per_user: int = 20) -> Dict[str, Any]:
    """Simulate realistic concurrent user load with varied query patterns."""
    print(f"🚀 Load Testing with {num_users} Concurrent Users")
    print("-" * 50)
    
    # Realistic query patterns based on user behavior
    query_patterns = {
        "executive_search": [
            "all hands meeting", "quarterly results", "team updates", "strategy",
            "budget", "roadmap", "hiring", "performance review"
        ],
        "project_search": [
            "project alpha", "deadline", "milestone", "deliverable", 
            "sprint planning", "standup", "retrospective", "blocker"
        ],
        "general_search": [
            "company", "team", "meeting", "update", "announcement",
            "lunch", "office hours", "help", "question"
        ],
        "specific_search": [
            "engineering", "product", "design", "marketing", "sales",
            "hr", "finance", "legal", "operations", "support"
        ]
    }
    
    def simulate_user(user_id: int) -> List[Dict[str, Any]]:
        """Simulate a single user's search session."""
        user_results = []
        
        # Connect to database (each user gets own connection)
        conn = sqlite3.connect('search.db')
        cursor = conn.cursor()
        
        # Simulate user behavior - mix of different query types
        pattern_weights = [0.2, 0.3, 0.4, 0.1]  # Bias toward general searches
        
        for query_num in range(queries_per_user):
            # Choose query pattern based on weights
            pattern = random.choices(list(query_patterns.keys()), weights=pattern_weights)[0]
            query_term = random.choice(query_patterns[pattern])
            
            # Add some variation
            if random.random() < 0.3:  # 30% chance of AND query
                second_term = random.choice(query_patterns[pattern])
                query_term = f"{query_term} AND {second_term}"
            elif random.random() < 0.1:  # 10% chance of phrase query
                query_term = f'"{query_term}"'
            
            # Execute search
            start_time = time.perf_counter()
            try:
                cursor.execute("SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH ?", (query_term,))
                result_count = cursor.fetchone()[0]
                search_time = time.perf_counter() - start_time
                
                user_results.append({
                    "user_id": user_id,
                    "query_num": query_num,
                    "pattern": pattern,
                    "query": query_term,
                    "search_time": search_time,
                    "result_count": result_count,
                    "success": True
                })
                
                # Realistic user behavior - brief pause between searches
                time.sleep(random.uniform(0.1, 0.5))
                
            except Exception as e:
                user_results.append({
                    "user_id": user_id,
                    "query_num": query_num,
                    "pattern": pattern,
                    "query": query_term,
                    "search_time": 0,
                    "result_count": 0,
                    "success": False,
                    "error": str(e)
                })
        
        conn.close()
        return user_results
    
    # Run concurrent user simulation
    print(f"   👥 Starting {num_users} users with {queries_per_user} queries each...")
    start_time = time.perf_counter()
    
    all_results = []
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(simulate_user, user_id) for user_id in range(num_users)]
        
        for future in as_completed(futures):
            user_results = future.result()
            all_results.extend(user_results)
    
    total_time = time.perf_counter() - start_time
    
    # Analyze results
    successful_queries = [r for r in all_results if r["success"]]
    failed_queries = [r for r in all_results if not r["success"]]
    
    if successful_queries:
        search_times = [r["search_time"] for r in successful_queries]
        avg_time = sum(search_times) / len(search_times)
        p95_time = sorted(search_times)[int(len(search_times) * 0.95)]
        p99_time = sorted(search_times)[int(len(search_times) * 0.99)]
        max_time = max(search_times)
        
        # Pattern analysis
        pattern_stats = {}
        for pattern in query_patterns.keys():
            pattern_results = [r for r in successful_queries if r["pattern"] == pattern]
            if pattern_results:
                pattern_times = [r["search_time"] for r in pattern_results]
                pattern_stats[pattern] = {
                    "count": len(pattern_results),
                    "avg_time": sum(pattern_times) / len(pattern_times),
                    "max_time": max(pattern_times)
                }
        
        return {
            "test_config": {
                "num_users": num_users,
                "queries_per_user": queries_per_user,
                "total_queries": len(all_results)
            },
            "execution": {
                "total_time": total_time,
                "queries_per_second": len(successful_queries) / total_time,
                "concurrent_users_supported": num_users
            },
            "performance": {
                "successful_queries": len(successful_queries),
                "failed_queries": len(failed_queries),
                "success_rate": len(successful_queries) / len(all_results) * 100,
                "avg_search_time": avg_time,
                "p95_search_time": p95_time,
                "p99_search_time": p99_time,
                "max_search_time": max_time
            },
            "pattern_analysis": pattern_stats,
            "performance_targets": {
                "avg_under_1s": avg_time < 1.0,
                "p95_under_2s": p95_time < 2.0,
                "p99_under_5s": p99_time < 5.0,
                "success_rate_over_95": len(successful_queries) / len(all_results) > 0.95
            }
        }
    else:
        return {"error": "No successful queries completed"}

def stress_test_database() -> Dict[str, Any]:
    """Stress test the database with extreme concurrent load."""
    print("💪 Stress Testing Database Limits")
    print("-" * 50)
    
    stress_levels = [10, 25, 50, 100]  # Number of concurrent connections
    results = {}
    
    for stress_level in stress_levels:
        print(f"   🔥 Testing {stress_level} concurrent connections...")
        
        def stress_worker():
            """Single stress test worker."""
            try:
                conn = sqlite3.connect('search.db')
                cursor = conn.cursor()
                
                start_time = time.perf_counter()
                
                # Perform rapid queries
                for _ in range(10):
                    cursor.execute("SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'test'")
                    cursor.fetchone()
                
                total_time = time.perf_counter() - start_time
                conn.close()
                
                return {"success": True, "time": total_time}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Run stress test
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=stress_level) as executor:
            futures = [executor.submit(stress_worker) for _ in range(stress_level)]
            worker_results = [future.result() for future in as_completed(futures)]
        
        test_time = time.perf_counter() - start_time
        
        successful_workers = [r for r in worker_results if r["success"]]
        failed_workers = [r for r in worker_results if not r["success"]]
        
        results[f"{stress_level}_connections"] = {
            "concurrent_connections": stress_level,
            "successful_workers": len(successful_workers),
            "failed_workers": len(failed_workers),
            "success_rate": len(successful_workers) / len(worker_results) * 100,
            "total_test_time": test_time,
            "database_stable": len(failed_workers) == 0
        }
        
        print(f"     ✅ {len(successful_workers)}/{len(worker_results)} workers succeeded")
        
        if len(failed_workers) > 0:
            print(f"     ⚠️  {len(failed_workers)} workers failed - database limit reached")
            break
    
    return results

def main():
    """Run advanced performance tests."""
    print("🚀 Advanced Performance Testing Suite")
    print("=" * 60)
    
    # Test 1: Query profiling
    print("\n1. Database Query Profiling")
    profiling_results = profile_database_queries()
    
    print(f"   📊 Database contains {profiling_results['total_messages']:,} messages")
    print(f"   📊 {profiling_results['slow_queries']} slow queries identified")
    
    # Test 2: Load testing
    print("\n2. Concurrent User Load Testing")
    load_results = load_test_concurrent_users(25, 10)  # 25 users, 10 queries each
    
    if "performance" in load_results:
        perf = load_results["performance"]
        print(f"   👥 {load_results['test_config']['num_users']} users completed {perf['successful_queries']} queries")
        print(f"   ⏱️  Average search time: {perf['avg_search_time']*1000:.1f}ms")
        print(f"   📊 95th percentile: {perf['p95_search_time']*1000:.1f}ms")
        print(f"   ✅ Success rate: {perf['success_rate']:.1f}%")
    
    # Test 3: Stress testing
    print("\n3. Database Stress Testing")
    stress_results = stress_test_database()
    
    max_connections = max([int(k.split('_')[0]) for k in stress_results.keys()])
    print(f"   💪 Database handled up to {max_connections} concurrent connections")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 ADVANCED PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    
    # Performance assessment
    database_healthy = profiling_results['slow_queries'] < 3
    load_handling = load_results.get("performance_targets", {}).get("p95_under_2s", False)
    stress_tolerance = any(r["database_stable"] for r in stress_results.values())
    
    print(f"   🔍 Database Query Health: {'✅ GOOD' if database_healthy else '⚠️ NEEDS OPTIMIZATION'}")
    print(f"   👥 Concurrent Load Handling: {'✅ EXCELLENT' if load_handling else '⚠️ NEEDS IMPROVEMENT'}")  
    print(f"   💪 Stress Tolerance: {'✅ ROBUST' if stress_tolerance else '❌ FRAGILE'}")
    
    # Save detailed results
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query_profiling": profiling_results,
        "load_testing": load_results,
        "stress_testing": stress_results,
        "assessment": {
            "database_healthy": database_healthy,
            "load_handling": load_handling,
            "stress_tolerance": stress_tolerance,
            "overall_score": sum([database_healthy, load_handling, stress_tolerance])
        }
    }
    
    import json
    with open("advanced_performance_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: advanced_performance_results.json")
    
    return results["assessment"]["overall_score"]

if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= 2 else 1)  # Pass if 2/3 or better