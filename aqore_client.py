"""
Aqore API Client - Wrapper for Hackathon API endpoints
Generated from Swagger specification
"""

import requests
import asyncio
from typing import List, Dict, Any, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class AqoreAPIClient:
    """Client for interacting with Aqore Hackathon API"""
    
    def __init__(self):
        self.base_url = settings.AQORE_API_BASE
        self.session = requests.Session()
        
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to Aqore API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Aqore API request failed: {url} - {e}")
            raise
    
    # Client endpoints
    def get_clients(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of clients"""
        return self._get("/Client/GetClients", {"PageNumber": page_number})
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients"""
        return self._get("/Client/GetAllClients")
    
    def get_client_by_id(self, client_id: int) -> Dict[str, Any]:
        """Get client by ID"""
        return self._get("/Client/GetClientById", {"clientId": client_id})
    
    # Job endpoints
    def get_jobs(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of jobs"""
        return self._get("/Job/GetJobs", {"PageNumber": page_number})
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs"""
        return self._get("/Job/GetAllJobs")
    
    def get_jobs_by_client_id(self, client_id: int) -> List[Dict[str, Any]]:
        """Get jobs by client ID"""
        return self._get("/Job/GetJobsByClientId", {"clientId": client_id})
    
    # JobSkill endpoints
    def get_job_skills(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of job skills"""
        return self._get("/JobSkill/GetJobSkills", {"PageNumber": page_number})
    
    def get_all_job_skills(self) -> List[Dict[str, Any]]:
        """Get all job skills"""
        return self._get("/JobSkill/GetAllJobSkills")
    
    def get_job_skills_by_job_id(self, job_id: int) -> List[Dict[str, Any]]:
        """Get job skills by job ID"""
        return self._get("/JobSkill/GetJobSkillsByJobId", {"jobId": job_id})
    
    # Person endpoints  
    def get_persons(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of persons"""
        return self._get("/Person/GetPersons", {"PageNumber": page_number})
    
    def get_all_persons(self) -> List[Dict[str, Any]]:
        """Get all persons"""
        return self._get("/Person/GetAllPersons")
    
    def get_person_by_id(self, person_id: int) -> Dict[str, Any]:
        """Get person by ID"""
        return self._get("/Person/GetPersonById", {"personId": person_id})
    
    # PersonEducation endpoints
    def get_person_educations(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of person educations"""
        return self._get("/PersonEducation/GetPersonEducations", {"PageNumber": page_number})
    
    def get_person_education_by_person_id(self, person_id: int) -> Dict[str, Any]:
        """Get person education by person ID"""
        return self._get("/PersonEducation/GetPersonEducationByPersonId", {"personId": person_id})
    
    # PersonEmployment endpoints
    def get_person_employments(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of person employments"""
        return self._get("/PersonEmployment/GetPersonEmployments", {"PageNumber": page_number})
    
    def get_person_employment_by_person_id(self, person_id: int) -> Dict[str, Any]:
        """Get person employment by person ID"""
        return self._get("/PersonEmployment/GetPersonEmploymentByPersonId", {"PersonId": person_id})
    
    # PersonResume endpoints
    def get_person_resume_by_person_id(self, person_id: int) -> Dict[str, Any]:
        """Get person resume by person ID"""
        return self._get("/PersonResume/GetPersonResumeByPersonId", {"personId": person_id})
    
    def download_resume(self, person_id: int) -> bytes:
        """Download resume file by person ID"""
        url = f"{self.base_url}/PersonResume/DownloadResume"
        response = self.session.get(url, params={"personId": person_id}, timeout=30)
        response.raise_for_status()
        return response.content
    
    # PersonSkill endpoints
    def get_person_skills(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Get paginated list of person skills"""
        return self._get("/PersonSkill/GetPersonSkills", {"PageNumber": page_number})
    
    def get_person_skill_by_person_id(self, person_id: int) -> List[Dict[str, Any]]:
        """Get person skills by person ID"""
        return self._get("/PersonSkill/GetPersonSkillByPersonId", {"personId": person_id})


# Global client instance
aqore_client = AqoreAPIClient()
