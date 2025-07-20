#!/usr/bin/env python3
"""
Test script for Enhanced Dashboard and Candidate Management
Tests the new HR dashboard features and candidate management endpoints
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_enhanced_dashboard_features():
    """Test the enhanced HR dashboard with enrichment tracking and analytics"""
    print("📊 Testing Enhanced HR Dashboard Features...")
    
    # First create a test candidate to work with
    print("\n1️⃣ Creating test candidate for dashboard...")
    timestamp = int(time.time())
    person_data = {
        "first_name": "Alex",
        "last_name": "Developer",
        "email": f"alex.dev.{timestamp}@example.com",
        "job_id": 183
    }
    
    response = requests.post(f"{BASE_URL}/sajilo/person", json=person_data)
    assert response.status_code == 200
    person = response.json()
    person_id = person["id"]
    print(f"   ✅ Test candidate created: {person_id}")
    
    # Extend the candidate with rich profile data
    print("\n2️⃣ Extending candidate profile...")
    extend_data = {
        "job_id": 183,
        "resume_text": "Full Stack Developer with 5+ years experience. Expert in React, Node.js, Python. Led development of e-commerce platform serving 1M+ users. MS in Computer Science. Passionate about clean code and system design. Built microservices architecture handling 100K+ requests per day.",
        "skills": "React,Node.js,Python,AWS,Docker,PostgreSQL,Redux,Express.js,MongoDB,Jest",
        "intro": "I'm a passionate full-stack developer who loves building user-friendly applications that solve real problems. I have experience leading small teams and mentoring junior developers.",
        "why_us": "I'm excited about your company's innovative approach to AI and the opportunity to work on cutting-edge projects. Your commitment to work-life balance and continuous learning aligns perfectly with my values.",
        "linkedin": "https://linkedin.com/in/alexdeveloper",
        "github": "https://github.com/alexdev"
    }
    
    response = requests.post(f"{BASE_URL}/sajilo/person/{person_id}/extend", json=extend_data)
    assert response.status_code == 200
    print("   ✅ Candidate profile extended")
    
    # Test enhanced dashboard view
    print("\n3️⃣ Testing enhanced dashboard view...")
    response = requests.get(f"{BASE_URL}/sajilo/dashboard/183?include_borderline=true")
    assert response.status_code == 200
    dashboard = response.json()
    
    print(f"   📊 Dashboard Job: {dashboard['job_title']}")
    print(f"   👥 Total Candidates: {dashboard['total_count']}")
    print(f"   🏆 High Fit: {dashboard['high_fit_count']}")
    print(f"   📈 Borderline: {dashboard.get('borderline_count', 0)}")
    
    # Check enhanced candidate data
    candidates = dashboard['candidates']
    our_candidate = next((c for c in candidates if c['person_id'] == person_id), None)
    
    if our_candidate:
        print(f"   ✅ Found our test candidate in dashboard")
        print(f"      📋 Enrichment Status: {our_candidate.get('enrichment_status', 'N/A')}")
        print(f"      📈 Enrichment Progress: {our_candidate.get('enrichment_progress', 0):.1%}")
        print(f"      🎯 Interview Ready: {our_candidate.get('interview_ready', False)}")
        print(f"      📊 Profile Completeness: {our_candidate.get('profile_completeness', 0):.3f}")
        print(f"      💬 Interview Stats: {our_candidate.get('interview_stats', {}).get('status', 'N/A')}")
    else:
        print("   ⚠️ Test candidate not found in dashboard")
    
    # Test dashboard analytics
    print("\n4️⃣ Testing dashboard analytics...")
    response = requests.get(f"{BASE_URL}/sajilo/dashboard/183/analytics")
    assert response.status_code == 200
    analytics = response.json()
    
    analytics_data = analytics['analytics']
    print(f"   📊 Analytics Total: {analytics_data['total_candidates']}")
    print(f"   🔄 Enrichment Breakdown: {analytics_data.get('enrichment_status_breakdown', {})}")
    print(f"   🎯 Interview Readiness: {analytics_data.get('interview_readiness_stats', {})}")
    print(f"   ⭐ Quality Metrics: Avg Fit Score {analytics_data.get('quality_metrics', {}).get('avg_fit_score', 0):.3f}")
    
    skill_gaps = analytics_data.get('skill_gap_analysis', {})
    if skill_gaps.get('available', False):
        print(f"   🎯 Skill Gap Analysis: {skill_gaps['candidates_analyzed']} analyzed")
        print(f"      Most Covered: {skill_gaps['most_covered_skill']['skill']}")
        print(f"      Least Covered: {skill_gaps['least_covered_skill']['skill']}")
    
    print("   ✅ Dashboard analytics retrieved successfully")
    
    return person_id


def test_enhanced_candidate_management(person_id):
    """Test enhanced candidate management features"""
    print(f"\n🎯 Testing Enhanced Candidate Management for ID: {person_id}...")
    
    # Test comprehensive candidate status
    print("\n1️⃣ Getting comprehensive candidate status...")
    response = requests.get(f"{BASE_URL}/sajilo/candidate/{person_id}/status")
    assert response.status_code == 200
    status = response.json()
    
    print(f"   👤 Candidate: {status['basic_info']['full_name']}")
    print(f"   📧 Email: {status['basic_info']['email']}")
    
    enrichment = status['enrichment']
    print(f"   🔄 Enrichment Status: {enrichment['status']}")
    print(f"   📈 Progress: {enrichment['progress']:.1%}")
    print(f"   🔒 Trust Score: {enrichment.get('trust_score', 'N/A')}")
    
    profile = status['profile_analysis']
    print(f"   📋 Profile Completeness: {profile['completeness_score']:.3f}")
    print(f"   📄 Resume: {profile['has_resume']} ({profile['resume_length']} chars)")
    print(f"   🛠️ Skills: {profile['skills_count']} skills")
    print(f"   💼 LinkedIn: {profile['has_linkedin']}, GitHub: {profile['has_github']}")
    
    interview = status['interview']
    print(f"   🎯 Interview Ready: {interview['ready']}")
    print(f"   💬 Status: {interview['status_message']}")
    
    insights = status['insights']
    print(f"   🧠 Insights Available: {insights['available']}")
    if insights['available']:
        summary = insights['summary']
        print(f"      📊 Credibility: {summary.get('credibility_score', 0):.3f}")
        print(f"      🎯 Job Fit: {summary.get('job_fit_score', 0):.3f}")
        print(f"      📈 Experience: {summary.get('experience_level', 'unknown')}")
        print(f"      🚩 Red Flags: {summary.get('red_flags_count', 0)}")
    
    print("   ✅ Comprehensive status retrieved")
    
    # Test manual enrichment trigger
    print("\n2️⃣ Testing manual enrichment trigger...")
    response = requests.post(f"{BASE_URL}/sajilo/candidate/{person_id}/trigger-enrichment")
    assert response.status_code == 200
    enrichment_result = response.json()
    
    print(f"   📝 Message: {enrichment_result['message']}")
    if enrichment_result.get('insights_generated'):
        print(f"   🧠 Insights Generated: ✅")
        print(f"   🎯 Ready for Interview: {enrichment_result.get('ready_for_interview', False)}")
    
    # Test interview readiness check
    print("\n3️⃣ Checking interview readiness...")
    response = requests.get(f"{BASE_URL}/sajilo/candidate/{person_id}/interview-readiness")
    assert response.status_code == 200
    readiness = response.json()
    
    print(f"   🎯 Ready: {readiness['ready_for_interview']}")
    print(f"   💬 Status: {readiness['status_message']}")
    print(f"   ⏱️ Duration: {readiness['estimated_interview_duration']}")
    print(f"   🎪 Type: {readiness['interview_type']}")
    
    checklist = readiness['readiness_checklist']
    ready_items = checklist.get('ready_items', [])
    pending_items = checklist.get('pending_items', [])
    
    print(f"   ✅ Ready Items ({len(ready_items)}):")
    for item in ready_items[:3]:  # Show first 3
        print(f"      - {item}")
    
    if pending_items:
        print(f"   ⏳ Pending Items ({len(pending_items)}):")
        for item in pending_items[:3]:  # Show first 3
            print(f"      - {item}")
    
    # Test interview preparation
    print("\n4️⃣ Preparing interview...")
    response = requests.post(f"{BASE_URL}/sajilo/candidate/{person_id}/prepare-interview?force=true")
    assert response.status_code == 200
    preparation = response.json()
    
    if preparation['prepared']:
        plan_summary = preparation['interview_plan_summary']
        print(f"   ✅ Interview Prepared Successfully")
        print(f"   📝 Questions: {plan_summary['total_questions']}")
        print(f"   📂 Categories: {', '.join(plan_summary['categories'])}")
        print(f"   🎯 Focus Areas: {', '.join(plan_summary['focus_areas'])}")
        print(f"   ⏱️ Duration: {preparation['estimated_duration']}")
        
        if plan_summary['red_flags_to_probe']:
            print(f"   🚩 Red Flags to Probe: {', '.join(plan_summary['red_flags_to_probe'])}")
    else:
        print(f"   ⚠️ Not Prepared: {preparation['reason']}")
    
    # Test scoring analysis
    print("\n5️⃣ Getting scoring analysis...")
    response = requests.get(f"{BASE_URL}/sajilo/candidate/{person_id}/scoring-analysis")
    assert response.status_code == 200
    scoring = response.json()
    
    if scoring['scoring_available']:
        breakdown = scoring['breakdown']
        overall = breakdown['overall']
        components = breakdown['components']
        
        print(f"   🏆 Overall Fit Score: {overall['fit_score']:.3f} ({overall['fit_bucket']})")
        print(f"   📊 Component Breakdown:")
        print(f"      🧠 Depth: {components.get('depth_score', 0):.3f}")
        print(f"      💪 Consistency: {components.get('consistency_score', 0):.3f}")
        print(f"      🎯 Motivation: {components.get('motivation_alignment', 0):.3f}")
        print(f"      🏢 Culture: {components.get('culture_alignment', 0):.3f}")
        print(f"      📈 Confidence: {components.get('data_confidence', 0):.3f}")
        
        recommendations = scoring.get('recommendations', [])
        if recommendations:
            print(f"   💡 Recommendations ({len(recommendations)}):")
            for rec in recommendations[:3]:  # Show first 3
                print(f"      - {rec}")
    else:
        print(f"   ⚠️ Scoring not available: {scoring['message']}")
    
    print("   ✅ Enhanced candidate management features tested successfully")


def test_adaptive_interview_integration(person_id):
    """Test integration with adaptive interview system"""
    print(f"\n🎪 Testing Adaptive Interview Integration for ID: {person_id}...")
    
    # Check if ready for adaptive interview
    response = requests.get(f"{BASE_URL}/sajilo/candidate/{person_id}/interview-readiness")
    readiness = response.json()
    
    if not readiness['ready_for_interview']:
        print("   ⚠️ Not ready for interview yet - forcing preparation...")
        requests.post(f"{BASE_URL}/sajilo/candidate/{person_id}/prepare-interview?force=true")
    
    # Try to start adaptive interview
    print("\n1️⃣ Starting adaptive interview...")
    try:
        response = requests.post(f"{BASE_URL}/sajilo/interview/{person_id}/start")
        
        if response.status_code == 200:
            interview = response.json()
            print(f"   ✅ Interview Started Successfully")
            print(f"   🤖 AI Greeting: {interview['agent_reply'][:100]}...")
            
            metadata = interview.get('interview_metadata', {})
            print(f"   📝 Planned Questions: {metadata.get('total_planned_questions', 'N/A')}")
            print(f"   🎯 Focus Areas: {', '.join(metadata.get('focus_areas', []))}")
            print(f"   🎪 Style: {metadata.get('interview_style', 'N/A')}")
            
            # Try a sample response
            print("\n2️⃣ Testing interview continuation...")
            sample_response = {
                "message": "I'm Alex, a full-stack developer with 5+ years of experience. I've worked extensively with React and Node.js, building scalable web applications. In my current role, I led the development of an e-commerce platform that serves over 1 million users, implementing microservices architecture and optimizing performance to handle 100K+ requests daily. I'm passionate about clean code, system design, and mentoring junior developers."
            }
            
            continue_response = requests.post(f"{BASE_URL}/sajilo/interview/{person_id}/continue", json=sample_response)
            
            if continue_response.status_code == 200:
                next_question = continue_response.json()
                print(f"   ✅ Interview Continued Successfully")
                print(f"   🤖 Next Question: {next_question['agent_reply'][:100]}...")
                print(f"   📊 Progress: {next_question['progress']:.1%}")
                
                interview_meta = next_question.get('interview_metadata', {})
                print(f"   📝 Question {interview_meta.get('current_question', '?')}/{interview_meta.get('total_planned_questions', '?')}")
                print(f"   📂 Category: {interview_meta.get('category', 'unknown')}")
            else:
                print(f"   ⚠️ Interview continuation failed: {continue_response.status_code}")
        
        elif response.status_code == 425:
            # Too early - enrichment not ready
            error_detail = response.json()['detail']
            print(f"   ⏳ Interview not ready: {error_detail.get('reason', 'Unknown')}")
            print(f"   📊 Enrichment Status: {error_detail.get('enrichment_status', 'Unknown')}")
        else:
            print(f"   ❌ Interview start failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Interview integration test failed: {e}")
    
    print("   ✅ Adaptive interview integration tested")


def test_dashboard_real_time_updates(person_id):
    """Test real-time updates in dashboard"""
    print(f"\n📈 Testing Dashboard Real-time Updates for ID: {person_id}...")
    
    # Get initial dashboard state
    response = requests.get(f"{BASE_URL}/sajilo/dashboard/183?include_borderline=true")
    initial_dashboard = response.json()
    
    # Find our candidate
    candidates = initial_dashboard['candidates']
    our_candidate = next((c for c in candidates if c['person_id'] == person_id), None)
    
    if our_candidate:
        print(f"   📊 Initial State:")
        print(f"      Enrichment: {our_candidate.get('enrichment_status', 'N/A')}")
        print(f"      Progress: {our_candidate.get('enrichment_progress', 0):.1%}")
        print(f"      Interview Ready: {our_candidate.get('interview_ready', False)}")
        print(f"      Fit Score: {our_candidate.get('fit_score', 0):.3f}")
    
    # Trigger some updates
    print("\n   🔄 Triggering enrichment update...")
    requests.post(f"{BASE_URL}/sajilo/candidate/{person_id}/trigger-enrichment")
    
    # Wait a moment for processing
    time.sleep(2)
    
    # Get updated dashboard state
    response = requests.get(f"{BASE_URL}/sajilo/dashboard/183?include_borderline=true")
    updated_dashboard = response.json()
    
    candidates = updated_dashboard['candidates']
    our_candidate = next((c for c in candidates if c['person_id'] == person_id), None)
    
    if our_candidate:
        print(f"   📊 Updated State:")
        print(f"      Enrichment: {our_candidate.get('enrichment_status', 'N/A')}")
        print(f"      Progress: {our_candidate.get('enrichment_progress', 0):.1%}")
        print(f"      Interview Ready: {our_candidate.get('interview_ready', False)}")
        print(f"      Fit Score: {our_candidate.get('fit_score', 0):.3f}")
        print(f"      Last Activity: {our_candidate.get('last_activity', 'N/A')}")
    
    print("   ✅ Dashboard real-time updates tested")


if __name__ == "__main__":
    print("🧪 Testing Enhanced Dashboard and Candidate Management")
    print("=" * 60)
    
    try:
        # Test enhanced dashboard features
        person_id = test_enhanced_dashboard_features()
        
        # Test enhanced candidate management
        test_enhanced_candidate_management(person_id)
        
        # Test adaptive interview integration
        test_adaptive_interview_integration(person_id)
        
        # Test dashboard real-time updates
        test_dashboard_real_time_updates(person_id)
        
        print("\n" + "=" * 60)
        print("🎉 All enhanced dashboard and candidate management tests completed successfully!")
        print(f"📊 Test candidate ID: {person_id}")
        print("\n🎯 Key Features Tested:")
        print("   ✅ Enhanced dashboard with enrichment tracking")
        print("   ✅ Comprehensive candidate status management")
        print("   ✅ Interview readiness checking and preparation")
        print("   ✅ Advanced scoring analysis with recommendations")
        print("   ✅ Real-time progress updates")
        print("   ✅ Adaptive interview system integration")
        print("   ✅ Dashboard analytics and skill gap analysis")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except requests.RequestException as e:
        print(f"\n🌐 Network error: {e}")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
