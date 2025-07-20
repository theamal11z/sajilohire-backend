#!/usr/bin/env python3
"""
Test script to verify AI scoring system functionality
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        return False

def test_create_candidate():
    """Test creating a candidate"""
    try:
        # Create a test candidate
        candidate_data = {
            "first_name": "John",
            "last_name": "Doe", 
            "email": "john.doe.test@example.com",
            "phone": "+1234567890",
            "job_id": 18956  # Using the Health Information Manager job
        }
        
        response = requests.post(f"{BASE_URL}/sajilo/person", json=candidate_data)
        if response.status_code == 200:
            candidate = response.json()
            print(f"✅ Created candidate with ID: {candidate['id']}")
            return candidate['id']
        else:
            print(f"❌ Failed to create candidate: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating candidate: {e}")
        return None

def test_extend_candidate(candidate_id):
    """Test extending candidate with resume and details"""
    try:
        extend_data = {
            "job_id": 18956,
            "resume_text": "John Doe is an experienced Health Information Manager with 5 years of experience in RHIA/RHIT certification, EHR management, HIPAA compliance, and healthcare analytics. He has worked with major healthcare systems implementing electronic health records and ensuring data privacy compliance.",
            "skills": "RHIA, RHIT, EHR Management, HIPAA Compliance, Healthcare Analytics, Medical Coding",
            "intro": "I am a passionate healthcare information professional with a strong background in health information management and regulatory compliance.",
            "why_us": "I am excited about this opportunity because your organization is known for its innovative approach to healthcare technology and commitment to patient data security.",
            "linkedin": "https://linkedin.com/in/johndoe",
            "github": "https://github.com/johndoe"
        }
        
        response = requests.post(f"{BASE_URL}/sajilo/person/{candidate_id}/extend", json=extend_data)
        if response.status_code == 200:
            print("✅ Extended candidate profile")
            return True
        else:
            print(f"❌ Failed to extend candidate: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error extending candidate: {e}")
        return False

def test_ai_scoring(candidate_id):
    """Test AI scoring functionality"""
    try:
        # Test recompute score endpoint
        response = requests.post(f"{BASE_URL}/sajilo/candidate/{candidate_id}/recompute-score")
        if response.status_code == 200:
            score_result = response.json()
            print(f"✅ AI scoring completed:")
            print(f"   Fit Score: {score_result['fit_score']:.3f}")
            print(f"   Fit Bucket: {score_result['fit_bucket']}")
            print(f"   Scoring Method: {score_result['scoring_method']}")
            return True
        else:
            print(f"❌ AI scoring failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error in AI scoring: {e}")
        return False

def test_ai_analysis(candidate_id):
    """Test AI analysis endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/sajilo/candidate/{candidate_id}/ai-analysis")
        if response.status_code == 200:
            analysis = response.json()
            print("✅ AI analysis retrieved:")
            if 'ai_analysis' in analysis and analysis['ai_analysis']:
                ai_data = analysis['ai_analysis']
                print(f"   Overall Fit Score: {ai_data.get('overall_fit_score', 'N/A')}")
                print(f"   Hiring Recommendation: {ai_data.get('hiring_recommendation', 'N/A')}")
                print(f"   Confidence Level: {ai_data.get('confidence_level', 'N/A')}")
                if 'key_strengths' in ai_data:
                    print(f"   Key Strengths: {ai_data['key_strengths'][:2]}...")
            return True
        else:
            print(f"❌ AI analysis failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error in AI analysis: {e}")
        return False

def test_dashboard_with_candidate():
    """Test dashboard with our new candidate"""
    try:
        response = requests.get(f"{BASE_URL}/sajilo/dashboard/18956?include_borderline=true")
        if response.status_code == 200:
            dashboard = response.json()
            print(f"✅ Dashboard loaded with {dashboard['total_count']} candidates")
            if dashboard['total_count'] > 0:
                candidate = dashboard['candidates'][0]
                print(f"   First candidate: {candidate['full_name']} (Fit: {candidate['fit_score']:.3f})")
            return True
        else:
            print(f"❌ Dashboard failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error loading dashboard: {e}")
        return False

def main():
    print("🧪 Testing AI Scoring System")
    print("=" * 40)
    
    # Test 1: Server health
    if not test_health():
        print("❌ Server is not running. Please start the backend first.")
        sys.exit(1)
    
    # Test 2: Create candidate
    candidate_id = test_create_candidate()
    if not candidate_id:
        print("❌ Cannot proceed without a candidate")
        sys.exit(1)
    
    # Test 3: Extend candidate profile
    if not test_extend_candidate(candidate_id):
        print("❌ Failed to extend candidate profile")
        sys.exit(1)
    
    # Test 4: AI scoring
    if not test_ai_scoring(candidate_id):
        print("❌ AI scoring system failed")
        sys.exit(1)
    
    # Test 5: AI analysis
    if not test_ai_analysis(candidate_id):
        print("❌ AI analysis system failed") 
        sys.exit(1)
    
    # Test 6: Dashboard
    if not test_dashboard_with_candidate():
        print("❌ Dashboard integration failed")
        sys.exit(1)
    
    print("\n🎉 All AI scoring tests passed!")
    print(f"🔗 Test candidate ID: {candidate_id}")
    print(f"🌐 View candidate: http://localhost:3000/candidate/{candidate_id}")
    print(f"🤖 View AI analysis: http://localhost:3000/candidate/{candidate_id}/phantombuster")

if __name__ == "__main__":
    main()
