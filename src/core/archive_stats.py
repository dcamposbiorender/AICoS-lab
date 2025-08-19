#!/usr/bin/env python3
"""
Enhanced Archive Statistics Engine
Provides comprehensive statistics calculation with optimization recommendations

Features:
- Detailed file analysis with age distribution
- Compression efficiency metrics  
- Source-by-source breakdown
- Health scoring with recommendations
- Performance optimization suggestions
"""

import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
import logging
import time

logger = logging.getLogger(__name__)


class ArchiveStats:
    """
    Calculate comprehensive archive statistics with optimization recommendations
    
    Features:
    - File count and size analysis by source and age
    - Compression efficiency calculation
    - Health scoring based on multiple factors
    - Actionable optimization recommendations
    - Performance metrics for large archives
    """
    
    def __init__(self):
        self.stats = {}
        self.scan_start_time = None
    
    def calculate(self, archive_dir: Path) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for an archive directory
        
        Args:
            archive_dir: Path to archive directory
            
        Returns:
            Dictionary with detailed statistics and recommendations
        """
        self.scan_start_time = time.time()
        
        stats = {
            'archive_directory': str(archive_dir),
            'timestamp': datetime.now().isoformat(),
            'total_files': 0,
            'uncompressed_files': 0,
            'compressed_files': 0,
            'total_size_mb': 0.0,
            'original_size_mb': 0.0,  # Estimated uncompressed size
            'compression_ratio': 0.0,
            'space_saved_mb': 0.0,
            'by_source': {},
            'age_distribution': {
                'week': {'count': 0, 'size_mb': 0.0},
                'month': {'count': 0, 'size_mb': 0.0}, 
                'year': {'count': 0, 'size_mb': 0.0},
                'ancient': {'count': 0, 'size_mb': 0.0}
            },
            'file_types': {
                'jsonl': {'count': 0, 'size_mb': 0.0},
                'compressed': {'count': 0, 'size_mb': 0.0},
                'manifest': {'count': 0, 'size_mb': 0.0},
                'other': {'count': 0, 'size_mb': 0.0}
            },
            'health_score': 0,
            'recommendations': [],
            'performance': {
                'scan_duration': 0.0,
                'files_per_second': 0.0
            }
        }
        
        if not archive_dir.exists():
            logger.warning(f"Archive directory does not exist: {archive_dir}")
            return stats
        
        # Calculate cutoff dates for age analysis
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        year_ago = now - timedelta(days=365)
        
        # Process each source directory
        try:
            self._scan_directory(archive_dir, stats, week_ago, month_ago, year_ago)
        except Exception as e:
            logger.error(f"Error scanning archive directory: {e}")
            stats['error'] = str(e)
            return stats
        
        # Calculate derived metrics
        self._calculate_derived_metrics(stats)
        
        # Generate health score and recommendations
        stats['health_score'] = self._calculate_health_score(stats)
        stats['recommendations'] = self._generate_recommendations(stats)
        
        # Performance metrics
        scan_duration = time.time() - self.scan_start_time
        stats['performance']['scan_duration'] = scan_duration
        if scan_duration > 0:
            stats['performance']['files_per_second'] = stats['total_files'] / scan_duration
        
        return stats
    
    def _scan_directory(self, archive_dir: Path, stats: Dict, week_ago: datetime, 
                       month_ago: datetime, year_ago: datetime):
        """Scan archive directory and collect file statistics"""
        
        for item in archive_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # This is a source directory (slack, calendar, etc.)
                source_name = item.name
                source_stats = {
                    'files': 0,
                    'size_mb': 0.0,
                    'compressed_files': 0,
                    'uncompressed_files': 0,
                    'days_of_data': 0,
                    'latest': None,
                    'oldest': None,
                    'avg_file_size_mb': 0.0
                }
                
                self._scan_source_directory(item, source_stats, stats, 
                                          week_ago, month_ago, year_ago)
                
                # Calculate averages
                if source_stats['files'] > 0:
                    source_stats['avg_file_size_mb'] = source_stats['size_mb'] / source_stats['files']
                
                stats['by_source'][source_name] = source_stats
    
    def _scan_source_directory(self, source_dir: Path, source_stats: Dict, 
                              stats: Dict, week_ago: datetime, month_ago: datetime, year_ago: datetime):
        """Scan individual source directory"""
        
        date_dirs = set()
        
        # Recursively scan all files in source directory
        for file_path in source_dir.rglob('*'):
            if not file_path.is_file():
                continue
            
            try:
                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 ** 2)
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # Update totals
                stats['total_files'] += 1
                stats['total_size_mb'] += file_size_mb
                source_stats['files'] += 1
                source_stats['size_mb'] += file_size_mb
                
                # Track date range
                if source_stats['latest'] is None or file_mtime.isoformat() > source_stats['latest']:
                    source_stats['latest'] = file_mtime.isoformat()
                if source_stats['oldest'] is None or file_mtime.isoformat() < source_stats['oldest']:
                    source_stats['oldest'] = file_mtime.isoformat()
                
                # Check for date directories
                parent_name = file_path.parent.name
                if parent_name.count('-') == 2:  # Likely YYYY-MM-DD format
                    date_dirs.add(parent_name)
                
                # Categorize by file type
                self._categorize_file(file_path, file_size_mb, stats, source_stats)
                
                # Age distribution
                self._update_age_distribution(file_mtime, file_size_mb, stats, 
                                            week_ago, month_ago, year_ago)
                
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not analyze file {file_path}: {e}")
        
        source_stats['days_of_data'] = len(date_dirs)
    
    def _categorize_file(self, file_path: Path, file_size_mb: float, 
                        stats: Dict, source_stats: Dict):
        """Categorize file by type and update statistics"""
        
        if file_path.suffix == '.jsonl':
            stats['file_types']['jsonl']['count'] += 1
            stats['file_types']['jsonl']['size_mb'] += file_size_mb
            stats['uncompressed_files'] += 1
            source_stats['uncompressed_files'] += 1
            stats['original_size_mb'] += file_size_mb
            
        elif file_path.suffixes == ['.jsonl', '.gz'] or file_path.suffix == '.gz':
            stats['file_types']['compressed']['count'] += 1
            stats['file_types']['compressed']['size_mb'] += file_size_mb
            stats['compressed_files'] += 1
            source_stats['compressed_files'] += 1
            # Estimate original size (assume 4:1 compression ratio)
            estimated_original = file_size_mb * 4
            stats['original_size_mb'] += estimated_original
            
        elif file_path.name == 'manifest.json':
            stats['file_types']['manifest']['count'] += 1
            stats['file_types']['manifest']['size_mb'] += file_size_mb
            
        else:
            stats['file_types']['other']['count'] += 1
            stats['file_types']['other']['size_mb'] += file_size_mb
    
    def _update_age_distribution(self, file_mtime: datetime, file_size_mb: float,
                                stats: Dict, week_ago: datetime, month_ago: datetime, year_ago: datetime):
        """Update age distribution statistics"""
        
        if file_mtime >= week_ago:
            stats['age_distribution']['week']['count'] += 1
            stats['age_distribution']['week']['size_mb'] += file_size_mb
        elif file_mtime >= month_ago:
            stats['age_distribution']['month']['count'] += 1
            stats['age_distribution']['month']['size_mb'] += file_size_mb
        elif file_mtime >= year_ago:
            stats['age_distribution']['year']['count'] += 1
            stats['age_distribution']['year']['size_mb'] += file_size_mb
        else:
            stats['age_distribution']['ancient']['count'] += 1
            stats['age_distribution']['ancient']['size_mb'] += file_size_mb
    
    def _calculate_derived_metrics(self, stats: Dict):
        """Calculate derived metrics like compression ratio"""
        
        # Compression ratio calculation
        if stats['original_size_mb'] > 0:
            stats['compression_ratio'] = 1 - (stats['total_size_mb'] / stats['original_size_mb'])
            stats['space_saved_mb'] = stats['original_size_mb'] - stats['total_size_mb']
    
    def _calculate_health_score(self, stats: Dict) -> int:
        """Calculate archive health score (0-100)"""
        
        if stats['total_files'] == 0:
            return 0
        
        score = 100
        
        # Compression efficiency (0-40 points)
        compression_ratio = stats.get('compression_ratio', 0)
        if compression_ratio > 0.7:  # >70% compression
            score -= 0  # Excellent
        elif compression_ratio > 0.5:  # >50% compression
            score -= 10  # Good
        elif compression_ratio > 0.3:  # >30% compression
            score -= 20  # Fair
        else:
            score -= 40  # Poor
        
        # File age distribution (0-30 points)
        old_files = (stats['age_distribution']['year']['count'] + 
                    stats['age_distribution']['ancient']['count'])
        old_ratio = old_files / stats['total_files'] if stats['total_files'] > 0 else 0
        
        if old_ratio > 0.5:  # >50% old files
            score -= 30
        elif old_ratio > 0.3:  # >30% old files  
            score -= 15
        elif old_ratio > 0.1:  # >10% old files
            score -= 5
        
        # Data source diversity (0-20 points)
        active_sources = sum(1 for source_stats in stats['by_source'].values() 
                           if source_stats['files'] > 0)
        if active_sources < 2:
            score -= 20
        elif active_sources < 3:
            score -= 10
        
        # File size distribution (0-10 points)
        avg_file_size = stats['total_size_mb'] / stats['total_files'] if stats['total_files'] > 0 else 0
        if avg_file_size < 0.1:  # Very small files
            score -= 10
        elif avg_file_size > 100:  # Very large files
            score -= 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Generate actionable optimization recommendations"""
        
        recommendations = []
        
        # Compression recommendations
        uncompressed_count = stats.get('uncompressed_files', 0)
        month_old_count = stats['age_distribution']['month']['count']
        year_old_count = stats['age_distribution']['year']['count']
        ancient_count = stats['age_distribution']['ancient']['count']
        
        if month_old_count > 10:
            potential_savings = month_old_count * 0.7  # Assume 70% compression
            recommendations.append(
                f"🗜️ Compress {month_old_count} files older than 30 days "
                f"(estimated savings: {potential_savings:.0f} files worth of space)"
            )
        
        if year_old_count > 50:
            recommendations.append(
                f"📁 Consider archiving {year_old_count} files older than 1 year to cold storage"
            )
        
        if ancient_count > 100:
            recommendations.append(
                f"🏛️ {ancient_count} very old files found - consider permanent archival or deletion"
            )
        
        # Storage recommendations
        total_size_gb = stats['total_size_mb'] / 1024
        if total_size_gb > 10:
            recommendations.append(
                f"💾 Large archive ({total_size_gb:.1f}GB) - implement automated retention policies"
            )
        
        # Data quality recommendations
        small_sources = sum(1 for source_stats in stats['by_source'].values() 
                          if source_stats['files'] > 0 and source_stats['size_mb'] < 1)
        if small_sources > 0:
            recommendations.append(
                f"⚠️ {small_sources} sources have minimal data - verify collectors are working"
            )
        
        # Performance recommendations
        if stats['total_files'] > 10000:
            recommendations.append(
                "⚡ Large file count - consider implementing file sharding for better performance"
            )
        
        # Health-based recommendations
        health_score = stats.get('health_score', 0)
        if health_score < 60:
            recommendations.append(
                "🏥 Archive health is concerning - review compression and retention policies"
            )
        
        return recommendations