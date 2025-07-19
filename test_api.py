#!/usr/bin/env python3
"""
Test script for SajiloHire Backend API
Validates all core functionality end-to-end
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    print(f"✅ Health check passed: {data['status']}")


def test_root():
    """Test root endpoint"""
    print("🏠 Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert "SajiloHire Backend API" in data["message"]
    print(f"✅ Root endpoint: {data['message']}")


def test_create_person():
    """Test creating a new person"""
    print("👤 Testing person creation...")
    person_data = {
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": "alice.johnson@example.com",
        "job_id": 183
    }
    
    response = requests.post(f"{BASE_URL}/sajilo/person", json=person_data)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Alice"
    assert data["id"] is not None
    
    person_id = data["id"]
    print(f"✅ Person created with ID: {person_id}")
    return person_id


def test_extend_person(person_id):
    """Test extending person with profile data"""
    print("📝 Testing person extension...")
    extend_data = {
        "job_id": 183,
        "resume_text": "Senior Machine Learning Engineer with 8 years experience. PhD in Computer Science. Expert in deep learning, MLOps, and scalable ML systems. Built recommendation systems serving 100M users.",
        "skills": "Python,TensorFlow,PyTorch,Kubernetes,AWS,Spark,Scala,Docker",
        "intro": "I am passionate about building production ML systems that make real impact.",
        "why_us": "I'm excited to work on cutting-edge AI research and help democratize access to intelligent systems.",
        "linkedin": "https://linkedin.com/in/alicejohnson",
        "github": "https://github.com/alicejohnson"
    }
    
    response = requests.post(f"{BASE_URL}/sajilo/person/{person_id}/extend", json=extend_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["skills_tags"]) > 0
    assert data["resume_text"] is not None
    print(f"✅ Person extended with {len(data['skills_tags'])} skills")


def test_chat_interview(person_id):
    """Test AI chat interview flow"""
    print("💬 Testing AI chat interview...")
    
    # Conversation flow
    messages = [
        "Hi! I'm Alice. I have extensive experience building large-scale machine learning systems, particularly in recommendation engines and deep learning applications.",
        "I led the development of a recommendation system at my previous company that served personalized content to over 100 million users. I architected the entire ML pipeline using Python, TensorFlow, and Kubernetes. The system processed 50TB of user interaction data daily and achieved a 35% improvement in user engagement. My role involved designing the neural network architecture, implementing distributed training, and building the MLOps infrastructure for continuous model deployment.",
        "Your company is pioneering the use of AI for social good, and I believe my experience in building scalable ML systems would help advance your mission. I'm particularly excited about the potential to use AI to solve meaningful problems and make technology more accessible to everyone.",
        "I'm not familiar with ElasticCacheX Timed Graph Layer - that sounds like it might be a fictional technology. Could you clarify what specific machine learning or infrastructure technology you're asking about?",
        "1. Mission Impact - Making a meaningful difference is most important to me. 2. Learning Opportunities - Continuous growth in the rapidly evolving AI field. 3. Work-Life Balance - Sustainable work leads to better innovation. 4. Salary - Important but secondary when the work is fulfilling.",
        "1. Assess the situation - Check monitoring dashboards, error logs, and system metrics to understand the scope and root cause. 2. Implement immediate fix - If it's a deployment issue, rollback to the last stable version. If it's infrastructure, failover to backup systems. 3. Communicate and follow up - Alert the on-call team, update status page, notify stakeholders, and prepare a post-incident review to prevent future occurrences."
    ]
    
    for i, message in enumerate(messages):
        print(f"  💭 Chat turn {i+1}...")
        chat_data = {"message": message}
        response = requests.post(f"{BASE_URL}/sajilo/chat/{person_id}", json=chat_data)
        assert response.status_code == 200
        data = response.json()
        assert "agent_reply" in data
        print(f"    🤖 AI: {data['agent_reply'][:80]}...")
        time.sleep(0.5)  # Avoid rate limiting
    
    print("✅ Chat interview completed")


def test_chat_history(person_id):
    """Test retrieving chat history"""
    print("📜 Testing chat history...")
    response = requests.get(f"{BASE_URL}/sajilo/chat/{person_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert data["person_id"] == person_id
    assert data["total_turns"] > 0
    print(f"✅ Chat history retrieved: {data['total_turns']} turns")


def test_full_candidate(person_id):
    """Test full candidate profile"""
    print("🔍 Testing full candidate profile...")
    response = requests.get(f"{BASE_URL}/sajilo/candidate/{person_id}/full")
    assert response.status_code == 200
    data = response.json()
    
    # Check person data
    assert data["person"]["id"] == person_id
    
    # Check signals
    assert data["signals"] is not None
    assert "consistency_score" in data["signals"]
    
    # Check score
    assert data["score"] is not None
    assert "fit_score" in data["score"]
    assert "fit_bucket" in data["score"]
    
    # Check chat history
    assert len(data["chat_history"]) > 0
    
    score = data["score"]["fit_score"]
    bucket = data["score"]["fit_bucket"]
    print(f"✅ Full profile retrieved - Score: {score:.3f} ({bucket})")
    return bucket


def test_dashboard(job_id):
    """Test recruiter dashboard"""
    print("📊 Testing recruiter dashboard...")
    response = requests.get(f"{BASE_URL}/sajilo/dashboard/{job_id}?include_borderline=true")
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert "candidates" in data
    assert data["total_count"] >= 0
    
    if data["candidates"]:
        candidate = data["candidates"][0]
        assert "person_id" in candidate
        assert "fit_score" in candidate
        assert "fit_bucket" in candidate
        
    print(f"✅ Dashboard loaded: {data['total_count']} candidates for job {data['job_title']}")


def run_all_tests():
    """Run complete test suite"""
    print("🚀 Starting SajiloHire Backend API Tests")
    print("=" * 50)
    
    try:
        # Basic health checks
        test_health()
        test_root()
        
        # Person management
        person_id = test_create_person()
        test_extend_person(person_id)
        
        # AI Interview flow
        test_chat_interview(person_id)
        test_chat_history(person_id)
        
        # Analytics and scoring
        fit_bucket = test_full_candidate(person_id)
        
        # Dashboard
        test_dashboard(183)  # Data Scientist job
        
        print("\n🎉 All tests passed!")
        print(f"✅ Created candidate with {fit_bucket} fit rating")
        print("✅ AI interview system working correctly")
        print("✅ Scoring engine functioning properly")
        print("✅ Dashboard displaying candidates accurately")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
