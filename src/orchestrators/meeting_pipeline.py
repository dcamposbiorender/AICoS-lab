#!/usr/bin/env python3
"""
Meeting Pipeline - Phase 4 Orchestration Engine
Orchestrates end-to-end meeting notes processing workflow

This is the main orchestration engine that coordinates all four phases:
1. Phase 1: Email Detection and Processing
2. Phase 2: Google Docs Content Extraction  
3. Phase 3: Meeting-Email Correlation
4. Phase 4: Output Generation and Archiving

Architecture:
- MeetingPipeline: Main orchestration engine
- PipelineState: Manages processing state and recovery
- OutputGenerator: Creates unified reports and dashboards
- ProgressTracker: Real-time progress reporting

Usage:
    from src.orchestrators.meeting_pipeline import MeetingPipeline
    pipeline = MeetingPipeline()
    results = pipeline.process_directory("/Users/user/Downloads")
"""

import os
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Phase imports
try:
    from ..collectors.email_collector import EmailCollector
    from ..collectors.drive_collector import DriveCollector
    from ..correlators.meeting_correlator import MeetingCorrelator
    from ..correlators.correlation_models import CorrelationStatus, MatchType
    from ..queries.structured import StructuredExtractor
    from ..core.archive_writer import ArchiveWriter
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import some components: {e}")
    # Define minimal enums for fallback
    from enum import Enum
    class CorrelationStrategy(Enum):
        COMPOSITE = "composite"
    IMPORTS_AVAILABLE = False


class PipelinePhase(Enum):
    """Pipeline execution phases"""
    INITIALIZATION = "initialization"
    EMAIL_PROCESSING = "email_processing"      # Phase 1
    DOCS_PROCESSING = "docs_processing"        # Phase 2
    CORRELATION = "correlation"                # Phase 3
    OUTPUT_GENERATION = "output_generation"    # Phase 4
    ARCHIVING = "archiving"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStatus(Enum):
    """Overall pipeline status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


@dataclass
class PhaseResult:
    """Result from a single pipeline phase"""
    phase: PipelinePhase
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    records_processed: int
    errors: List[str]
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['phase'] = self.phase.value
        result['status'] = self.status.value
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat() if self.end_time else None
        return result


@dataclass 
class PipelineResults:
    """Complete pipeline execution results"""
    pipeline_id: str
    directory_processed: str
    start_time: datetime
    end_time: Optional[datetime]
    total_duration: float
    overall_status: PipelineStatus
    
    # Phase results
    phase_results: List[PhaseResult]
    
    # Aggregate data
    total_emails_found: int
    total_docs_found: int
    successful_correlations: int
    orphaned_records: int
    action_items_extracted: int
    
    # Output files
    output_files: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['overall_status'] = self.overall_status.value
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat() if self.end_time else None
        result['phase_results'] = [phase.to_dict() for phase in self.phase_results]
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get concise summary for reporting"""
        return {
            'pipeline_id': self.pipeline_id,
            'status': self.overall_status.value,
            'duration': self.total_duration,
            'files_processed': {
                'emails': self.total_emails_found,
                'docs': self.total_docs_found,
                'correlations': self.successful_correlations,
                'orphaned': self.orphaned_records
            },
            'action_items': self.action_items_extracted,
            'output_files': len(self.output_files)
        }


class ProgressTracker:
    """Real-time progress tracking and logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.current_phase = None
        self.phase_start_time = None
        self.total_phases = 6  # Total number of phases
        self.completed_phases = 0
    
    def start_phase(self, phase: PipelinePhase, description: str = ""):
        """Start tracking a new phase"""
        self.current_phase = phase
        self.phase_start_time = time.time()
        
        progress_pct = (self.completed_phases / self.total_phases) * 100
        phase_name = phase.value.replace('_', ' ').title()
        
        self.logger.info(f"🚀 Starting {phase_name} [{progress_pct:.0f}%] {description}")
        
    def update_progress(self, message: str, count: Optional[int] = None):
        """Update progress within current phase"""
        if count is not None:
            self.logger.info(f"   {message}: {count}")
        else:
            self.logger.info(f"   {message}")
    
    def complete_phase(self, records_processed: int = 0, errors: List[str] = None):
        """Complete current phase"""
        if self.phase_start_time:
            duration = time.time() - self.phase_start_time
            
            phase_name = self.current_phase.value.replace('_', ' ').title()
            error_msg = f", {len(errors)} errors" if errors else ""
            
            self.logger.info(f"✅ Completed {phase_name} in {duration:.1f}s "
                           f"({records_processed} records{error_msg})")
            
            self.completed_phases += 1
        
    def log_error(self, error: str):
        """Log an error during processing"""
        self.logger.error(f"❌ {error}")


class MeetingPipeline:
    """Main orchestration engine for meeting notes processing"""
    
    def __init__(self, 
                 correlation_strategy = None,
                 min_correlation_confidence: float = 0.6,
                 output_directory: Optional[str] = None):
        """
        Initialize meeting pipeline
        
        Args:
            correlation_strategy: Strategy for Phase 3 correlation
            min_correlation_confidence: Minimum confidence for correlations
            output_directory: Directory for output files (default: data/processed)
        """
        self.correlation_strategy = correlation_strategy
        self.min_correlation_confidence = min_correlation_confidence
        
        # Setup output directory
        if output_directory:
            self.output_directory = Path(output_directory)
        else:
            # Default to project data directory
            project_root = Path(__file__).parent.parent.parent
            self.output_directory = project_root / "data" / "processed" / "meetings"
        
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.MeetingPipeline")
        self.progress_tracker = ProgressTracker(self.logger)
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize pipeline components"""
        try:
            self.email_collector = EmailCollector()
            self.drive_collector = DriveCollector()
            self.correlator = MeetingCorrelator(
                strategy=self.correlation_strategy,
                min_confidence_threshold=self.min_correlation_confidence
            )
            self.structured_extractor = StructuredExtractor()
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _execute_phase_1(self, directory: str) -> PhaseResult:
        """Execute Phase 1: Email Processing"""
        phase = PipelinePhase.EMAIL_PROCESSING
        start_time = datetime.now(timezone.utc)
        errors = []
        email_records = []
        
        try:
            self.progress_tracker.start_phase(phase, "- Detecting and processing email files")
            
            # Detect email files
            email_files = self.email_collector.detect_meeting_notes_emails(directory)
            self.progress_tracker.update_progress(f"Found email files", len(email_files))
            
            if email_files:
                # Process emails
                try:
                    result = self.email_collector.collect_from_directory(directory)
                    email_records = result.email_records if hasattr(result, 'email_records') else []
                    
                    self.progress_tracker.update_progress(f"Successfully processed emails", result.emails_processed)
                    
                    if result.errors:
                        errors.extend(result.errors)
                        
                except Exception as e:
                    error_msg = f"Email processing failed: {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
            
            # Determine status
            status = PipelineStatus.COMPLETED_WITH_ERRORS if errors else PipelineStatus.COMPLETED_SUCCESS
            
            self.progress_tracker.complete_phase(len(email_records), errors)
            
            return PhaseResult(
                phase=phase,
                status=status,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=len(email_records),
                errors=errors,
                data=email_records
            )
            
        except Exception as e:
            error_msg = f"Phase 1 failed: {e}"
            errors.append(error_msg)
            self.progress_tracker.log_error(error_msg)
            
            return PhaseResult(
                phase=phase,
                status=PipelineStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=0,
                errors=errors,
                data=[]
            )
    
    def _execute_phase_2(self, directory: str) -> PhaseResult:
        """Execute Phase 2: Google Docs Processing"""
        phase = PipelinePhase.DOCS_PROCESSING
        start_time = datetime.now(timezone.utc)
        errors = []
        doc_records = []
        
        try:
            self.progress_tracker.start_phase(phase, "- Detecting and processing Google Docs files")
            
            # Process DOCX files
            try:
                result = self.drive_collector.collect_local_docx_files(directory)
                
                self.progress_tracker.update_progress(f"Found DOCX files", result['files_found'])
                self.progress_tracker.update_progress(f"Successfully processed", result['successful_extractions'])
                
                # Convert to list format expected by correlation
                doc_records = result.get('extracted_documents', [])
                
                if result['failed_extractions'] > 0:
                    error_msg = f"{result['failed_extractions']} DOCX files failed processing"
                    errors.append(error_msg)
                    
            except Exception as e:
                error_msg = f"DOCX processing failed: {e}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
            
            # Determine status
            status = PipelineStatus.COMPLETED_WITH_ERRORS if errors else PipelineStatus.COMPLETED_SUCCESS
            
            self.progress_tracker.complete_phase(len(doc_records), errors)
            
            return PhaseResult(
                phase=phase,
                status=status,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=len(doc_records),
                errors=errors,
                data=doc_records
            )
            
        except Exception as e:
            error_msg = f"Phase 2 failed: {e}"
            errors.append(error_msg)
            self.progress_tracker.log_error(error_msg)
            
            return PhaseResult(
                phase=phase,
                status=PipelineStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=0,
                errors=errors,
                data=[]
            )
    
    def _execute_phase_3(self, email_records: List[Dict[str, Any]], 
                        doc_records: List[Dict[str, Any]]) -> PhaseResult:
        """Execute Phase 3: Meeting-Email Correlation"""
        phase = PipelinePhase.CORRELATION
        start_time = datetime.now(timezone.utc)
        errors = []
        correlation_results = None
        
        try:
            self.progress_tracker.start_phase(phase, f"- Correlating {len(email_records)} emails with {len(doc_records)} docs")
            
            # Run correlation
            correlation_results = self.correlator.correlate_meetings(email_records, doc_records)
            
            self.progress_tracker.update_progress(f"Successful correlations", len(correlation_results.correlated_meetings))
            self.progress_tracker.update_progress(f"Orphaned emails", len(correlation_results.orphaned_emails))
            self.progress_tracker.update_progress(f"Orphaned docs", len(correlation_results.orphaned_docs))
            
            # Extract structured content
            self.correlator.extract_structured_content(correlation_results.correlated_meetings)
            
            # Calculate action items
            total_actions = sum(len(meeting.action_items) for meeting in correlation_results.correlated_meetings)
            self.progress_tracker.update_progress(f"Action items extracted", total_actions)
            
            status = PipelineStatus.COMPLETED_SUCCESS
            self.progress_tracker.complete_phase(len(correlation_results.correlated_meetings), errors)
            
            return PhaseResult(
                phase=phase,
                status=status,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=len(correlation_results.correlated_meetings),
                errors=errors,
                data=correlation_results
            )
            
        except Exception as e:
            error_msg = f"Phase 3 failed: {e}"
            errors.append(error_msg)
            self.progress_tracker.log_error(error_msg)
            
            return PhaseResult(
                phase=phase,
                status=PipelineStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=0,
                errors=errors,
                data=None
            )
    
    def _execute_phase_4(self, correlation_results, pipeline_id: str) -> Tuple[PhaseResult, List[str]]:
        """Execute Phase 4: Output Generation"""
        phase = PipelinePhase.OUTPUT_GENERATION
        start_time = datetime.now(timezone.utc)
        errors = []
        output_files = []
        
        try:
            self.progress_tracker.start_phase(phase, "- Generating reports and dashboards")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. Generate unified JSONL archive
            jsonl_file = self.output_directory / f"meetings_{pipeline_id}_{timestamp}.jsonl"
            self._write_jsonl_archive(correlation_results, jsonl_file)
            output_files.append(str(jsonl_file))
            self.progress_tracker.update_progress(f"Generated JSONL archive", 1)
            
            # 2. Generate summary report
            summary_file = self.output_directory / f"summary_{pipeline_id}_{timestamp}.json"
            self._write_summary_report(correlation_results, summary_file, pipeline_id)
            output_files.append(str(summary_file))
            self.progress_tracker.update_progress(f"Generated summary report", 1)
            
            # 3. Generate action items dashboard
            if correlation_results and correlation_results.correlated_meetings:
                dashboard_file = self.output_directory / f"dashboard_{pipeline_id}_{timestamp}.md"
                self._write_dashboard(correlation_results, dashboard_file)
                output_files.append(str(dashboard_file))
                self.progress_tracker.update_progress(f"Generated dashboard", 1)
            
            status = PipelineStatus.COMPLETED_SUCCESS
            self.progress_tracker.complete_phase(len(output_files), errors)
            
            return PhaseResult(
                phase=phase,
                status=status,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=len(output_files),
                errors=errors,
                data=output_files
            ), output_files
            
        except Exception as e:
            error_msg = f"Phase 4 failed: {e}"
            errors.append(error_msg)
            self.progress_tracker.log_error(error_msg)
            
            return PhaseResult(
                phase=phase,
                status=PipelineStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                records_processed=0,
                errors=errors,
                data=[]
            ), []
    
    def _write_jsonl_archive(self, correlation_results, output_file: Path):
        """Write unified JSONL archive"""
        import json
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if correlation_results:
                # Write correlated meetings
                for meeting in correlation_results.correlated_meetings:
                    f.write(json.dumps(meeting.to_dict()) + '\n')
                
                # Write orphaned records
                for orphaned in correlation_results.orphaned_emails + correlation_results.orphaned_docs:
                    f.write(json.dumps(orphaned.to_dict()) + '\n')
    
    def _write_summary_report(self, correlation_results, output_file: Path, pipeline_id: str):
        """Write summary report"""
        import json
        
        summary = {
            'pipeline_id': pipeline_id,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'correlation_summary': correlation_results.get_summary() if correlation_results else {},
            'metrics': correlation_results.correlation_metrics.to_dict() if correlation_results else {}
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
    
    def _write_dashboard(self, correlation_results, output_file: Path):
        """Write action items dashboard"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Meeting Notes Action Items Dashboard\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, meeting in enumerate(correlation_results.correlated_meetings, 1):
                f.write(f"## {i}. {meeting.meeting_title}\n")
                f.write(f"**Date:** {meeting.meeting_datetime.strftime('%Y-%m-%d %H:%M') if meeting.meeting_datetime else 'Unknown'}\n")
                f.write(f"**Participants:** {', '.join(meeting.participants)}\n")
                f.write(f"**Confidence:** {meeting.confidence_score:.2f}\n\n")
                
                if meeting.action_items:
                    f.write("### Action Items\n")
                    for j, action in enumerate(meeting.action_items, 1):
                        assignee = action.get('assignee', 'Unknown')
                        task = action.get('action', action.get('task', 'No description'))
                        f.write(f"{j}. **{assignee}**: {task}\n")
                    f.write("\n")
                else:
                    f.write("*No action items found*\n\n")
                
                f.write("---\n\n")
    
    def process_directory(self, directory: str) -> PipelineResults:
        """
        Main pipeline execution method
        
        Args:
            directory: Directory containing meeting notes files
            
        Returns:
            Complete pipeline results
        """
        # Generate unique pipeline ID
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(f"🚀 Starting Meeting Notes Pipeline [{pipeline_id}]")
        self.logger.info(f"📁 Processing directory: {directory}")
        self.logger.info(f"🎯 Strategy: {self.correlation_strategy.value}")
        
        phase_results = []
        overall_status = PipelineStatus.IN_PROGRESS
        
        try:
            # Phase 1: Email Processing
            phase1_result = self._execute_phase_1(directory)
            phase_results.append(phase1_result)
            email_records = phase1_result.data or []
            
            # Phase 2: Google Docs Processing  
            phase2_result = self._execute_phase_2(directory)
            phase_results.append(phase2_result)
            doc_records = phase2_result.data or []
            
            # Phase 3: Correlation (only if we have data)
            correlation_results = None
            if email_records or doc_records:
                phase3_result = self._execute_phase_3(email_records, doc_records)
                phase_results.append(phase3_result)
                correlation_results = phase3_result.data
            else:
                self.logger.warning("⚠️ No email or doc records found, skipping correlation")
            
            # Phase 4: Output Generation
            phase4_result, output_files = self._execute_phase_4(correlation_results, pipeline_id)
            phase_results.append(phase4_result)
            
            # Determine overall status
            failed_phases = [p for p in phase_results if p.status == PipelineStatus.FAILED]
            error_phases = [p for p in phase_results if p.status == PipelineStatus.COMPLETED_WITH_ERRORS]
            
            if failed_phases:
                overall_status = PipelineStatus.FAILED
            elif error_phases:
                overall_status = PipelineStatus.COMPLETED_WITH_ERRORS
            else:
                overall_status = PipelineStatus.COMPLETED_SUCCESS
                
        except Exception as e:
            self.logger.error(f"Pipeline failed with unexpected error: {e}")
            overall_status = PipelineStatus.FAILED
            output_files = []
        
        # Calculate totals
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()
        
        total_emails = len(email_records) if email_records else 0
        total_docs = len(doc_records) if doc_records else 0
        
        correlations = 0
        orphaned = 0
        actions = 0
        
        if correlation_results:
            correlations = len(correlation_results.correlated_meetings)
            orphaned = len(correlation_results.orphaned_emails) + len(correlation_results.orphaned_docs)
            actions = sum(len(m.action_items) for m in correlation_results.correlated_meetings)
        
        # Create results
        results = PipelineResults(
            pipeline_id=pipeline_id,
            directory_processed=directory,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            overall_status=overall_status,
            phase_results=phase_results,
            total_emails_found=total_emails,
            total_docs_found=total_docs,
            successful_correlations=correlations,
            orphaned_records=orphaned,
            action_items_extracted=actions,
            output_files=output_files or []
        )
        
        # Log final results
        self.logger.info(f"🎯 Pipeline Complete [{pipeline_id}]")
        self.logger.info(f"📊 Status: {overall_status.value}")
        self.logger.info(f"⏱️ Duration: {total_duration:.1f}s")
        self.logger.info(f"📈 Results: {correlations} correlations, {actions} action items")
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test with user's Downloads directory
    downloads_dir = "/Users/david.campos/Downloads"
    
    # Create and run pipeline
    pipeline = MeetingPipeline(
        correlation_strategy=CorrelationStrategy.COMPOSITE,
        min_correlation_confidence=0.5
    )
    
    results = pipeline.process_directory(downloads_dir)
    
    print("\n📊 Pipeline Results Summary:")
    summary = results.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    if results.output_files:
        print(f"\n📁 Output files generated:")
        for file_path in results.output_files:
            print(f"  - {file_path}")