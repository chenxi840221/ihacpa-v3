"""
Enhanced version parsing and comparison utilities for vulnerability assessment.
Addresses the issue where 131 packages require manual version checking.
"""

import re
import logging
from typing import List, Optional, Tuple, Union, Dict
from packaging import version
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)


class VersionParser:
    """Enhanced version parser with CVE description analysis capabilities."""
    
    def __init__(self):
        # Common version range patterns found in CVE descriptions
        self.version_patterns = [
            # Exact version patterns
            r'version\s+(\d+(?:\.\d+)*(?:\.\d+)*)',
            r'v(\d+(?:\.\d+)*(?:\.\d+)*)',
            r'(\d+(?:\.\d+)+)\s+and\s+earlier',
            r'(\d+(?:\.\d+)+)\s+or\s+earlier',
            r'before\s+(\d+(?:\.\d+)*)',
            r'prior\s+to\s+(\d+(?:\.\d+)*)',
            
            # Range patterns
            r'versions?\s+(\d+(?:\.\d+)*)\s+through\s+(\d+(?:\.\d+)*)',
            r'versions?\s+(\d+(?:\.\d+)*)\s+to\s+(\d+(?:\.\d+)*)',
            r'from\s+(\d+(?:\.\d+)*)\s+to\s+(\d+(?:\.\d+)*)',
            r'between\s+(\d+(?:\.\d+)*)\s+and\s+(\d+(?:\.\d+)*)',
            
            # Inequality patterns
            r'<\s*(\d+(?:\.\d+)*)',
            r'<=\s*(\d+(?:\.\d+)*)',
            r'>\s*(\d+(?:\.\d+)*)',
            r'>=\s*(\d+(?:\.\d+)*)',
            r'==\s*(\d+(?:\.\d+)*)',
            r'!=\s*(\d+(?:\.\d+)*)',
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.version_patterns]
    
    def parse_version_safely(self, version_str: str) -> Optional[Version]:
        """Safely parse version string, handling edge cases."""
        try:
            if not version_str:
                return None
            
            # Clean version string
            clean_version = str(version_str).strip()
            
            # Handle common prefixes
            if clean_version.startswith('v'):
                clean_version = clean_version[1:]
            
            # Remove extra whitespace and non-version characters
            clean_version = re.sub(r'[^\d\.]', '', clean_version)
            
            if not clean_version:
                return None
                
            return version.parse(clean_version)
        except (InvalidVersion, TypeError, ValueError) as e:
            logger.debug(f"Failed to parse version '{version_str}': {e}")
            return None
    
    def extract_version_ranges_from_cve(self, cve_description: str) -> List[Dict[str, Union[str, List[str]]]]:
        """
        Extract version ranges from CVE descriptions.
        Returns list of version constraints that can be used for comparison.
        """
        if not cve_description:
            return []
        
        constraints = []
        text = cve_description.lower()
        
        # Look for version patterns
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # Range pattern (e.g., "from X to Y")
                    start_version = self.parse_version_safely(match[0])
                    end_version = self.parse_version_safely(match[1])
                    if start_version and end_version:
                        constraints.append({
                            'type': 'range',
                            'start': str(start_version),
                            'end': str(end_version),
                            'specifier': f'>={start_version},<={end_version}'
                        })
                else:
                    # Single version constraint
                    parsed_version = self.parse_version_safely(match)
                    if parsed_version:
                        # Determine constraint type based on context
                        constraint_type = self._determine_constraint_type(text, str(parsed_version))
                        constraints.append({
                            'type': constraint_type,
                            'version': str(parsed_version),
                            'specifier': self._create_specifier(constraint_type, str(parsed_version))
                        })
        
        return constraints
    
    def _determine_constraint_type(self, text: str, version_str: str) -> str:
        """Determine the type of version constraint based on context."""
        version_context = text[max(0, text.find(version_str) - 50):text.find(version_str) + 50]
        
        if any(keyword in version_context for keyword in ['before', 'prior to', 'earlier']):
            return 'less_than'
        elif any(keyword in version_context for keyword in ['after', 'since', 'from']):
            return 'greater_than_equal'
        elif any(keyword in version_context for keyword in ['through', 'up to', 'until']):
            return 'less_than_equal'
        else:
            return 'equal'
    
    def _create_specifier(self, constraint_type: str, version_str: str) -> str:
        """Create a PEP 440 version specifier string."""
        if constraint_type == 'less_than':
            return f'<{version_str}'
        elif constraint_type == 'less_than_equal':
            return f'<={version_str}'
        elif constraint_type == 'greater_than':
            return f'>{version_str}'
        elif constraint_type == 'greater_than_equal':
            return f'>={version_str}'
        elif constraint_type == 'equal':
            return f'=={version_str}'
        else:
            return f'=={version_str}'
    
    def is_version_affected(self, package_version: str, cve_constraints: List[Dict]) -> Tuple[bool, float, List[str]]:
        """
        Check if a package version is affected by CVE constraints.
        Returns (is_affected, confidence_score, matching_constraints)
        """
        if not cve_constraints:
            return False, 0.0, []
        
        pkg_version = self.parse_version_safely(package_version)
        if not pkg_version:
            return False, 0.0, ["Unable to parse package version"]
        
        matching_constraints = []
        total_constraints = len(cve_constraints)
        matched_constraints = 0
        
        for constraint in cve_constraints:
            try:
                specifier_str = constraint.get('specifier', '')
                if specifier_str:
                    spec_set = SpecifierSet(specifier_str)
                    if pkg_version in spec_set:
                        matching_constraints.append(specifier_str)
                        matched_constraints += 1
            except (InvalidSpecifier, ValueError) as e:
                logger.debug(f"Invalid specifier '{constraint}': {e}")
                continue
        
        # Calculate confidence based on how many constraints matched
        confidence = matched_constraints / total_constraints if total_constraints > 0 else 0.0
        is_affected = matched_constraints > 0
        
        return is_affected, confidence, matching_constraints
    
    def compare_versions(self, version1: str, version2: str) -> Optional[int]:
        """
        Compare two versions. Returns:
        -1 if version1 < version2
        0 if version1 == version2  
        1 if version1 > version2
        None if comparison is not possible
        """
        v1 = self.parse_version_safely(version1)
        v2 = self.parse_version_safely(version2)
        
        if v1 is None or v2 is None:
            return None
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    
    def extract_versions_from_text(self, text: str) -> List[str]:
        """Extract all potential version numbers from text."""
        if not text:
            return []
        
        # Pattern to match version-like strings
        version_pattern = r'\b\d+(?:\.\d+){1,3}\b'
        matches = re.findall(version_pattern, text)
        
        # Validate and clean matches
        valid_versions = []
        for match in matches:
            if self.parse_version_safely(match):
                valid_versions.append(match)
        
        return list(set(valid_versions))  # Remove duplicates


class VulnerabilityVersionChecker:
    """Enhanced vulnerability checker with confidence scoring."""
    
    def __init__(self):
        self.version_parser = VersionParser()
    
    def check_vulnerability_applicability(
        self, 
        package_name: str,
        package_version: str, 
        cve_description: str,
        cve_id: str = None
    ) -> Dict[str, Union[bool, float, str, List]]:
        """
        Check if a vulnerability applies to a specific package version.
        Returns comprehensive analysis with confidence scoring.
        """
        result = {
            'package_name': package_name,
            'package_version': package_version,
            'cve_id': cve_id,
            'is_affected': False,
            'confidence_score': 0.0,
            'analysis_method': 'automated',
            'requires_manual_review': False,
            'extracted_constraints': [],
            'matching_constraints': [],
            'recommendation': 'SAFE'
        }
        
        # Extract version constraints from CVE description
        constraints = self.version_parser.extract_version_ranges_from_cve(cve_description)
        result['extracted_constraints'] = constraints
        
        if not constraints:
            # No version information found - requires manual review
            result['requires_manual_review'] = True
            result['analysis_method'] = 'manual_required'
            result['recommendation'] = 'MANUAL_REVIEW'
            result['confidence_score'] = 0.0
            return result
        
        # Check if package version is affected
        is_affected, confidence, matching = self.version_parser.is_version_affected(
            package_version, constraints
        )
        
        result['is_affected'] = is_affected
        result['confidence_score'] = confidence
        result['matching_constraints'] = matching
        
        # Determine recommendation based on confidence
        if confidence >= 0.8:
            result['recommendation'] = 'VULNERABLE' if is_affected else 'SAFE'
            result['analysis_method'] = 'high_confidence_automated'
        elif confidence >= 0.5:
            result['recommendation'] = 'LIKELY_VULNERABLE' if is_affected else 'LIKELY_SAFE'
            result['analysis_method'] = 'medium_confidence_automated'
        else:
            result['requires_manual_review'] = True
            result['recommendation'] = 'MANUAL_REVIEW'
            result['analysis_method'] = 'low_confidence_manual'
        
        return result


# Utility functions for backward compatibility
def parse_version_range(version_range_str: str) -> Optional[SpecifierSet]:
    """Parse version range string into SpecifierSet."""
    try:
        return SpecifierSet(version_range_str)
    except InvalidSpecifier:
        return None


def is_version_in_range(version_str: str, range_str: str) -> bool:
    """Check if version is in specified range."""
    parser = VersionParser()
    version_obj = parser.parse_version_safely(version_str)
    range_obj = parse_version_range(range_str)
    
    if version_obj is None or range_obj is None:
        return False
    
    return version_obj in range_obj