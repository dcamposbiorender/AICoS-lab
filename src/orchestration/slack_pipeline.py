#!/usr/bin/env python3
"""
Slack-Focused Pipeline Orchestrator - Phase 6A Implementation
Implements the revised Phase 6 scope: basic integration between Slack collection → intelligence → results aggregation
Following acceptance criteria for realistic, incremental approach.
"""

import sys
import time
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Import Phase 1 and Phase 5 components
from ..collectors.slack_collector import SlackCollector
from ..collectors.slack_intelligence import SlackIntelligence
from ..core.slack_state_manager import SlackStateManager
from ..extractors.slack_structured import SlackStructuredExtractor

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Pipeline execution modes as per AC A1.2"""
    INCREMENTAL = "incremental"  # Default mode
    FULL_REFRESH = "full_refresh"


class ComponentStatus(Enum):
    """Component status for health monitoring"""
    HEALTHY = "healthy"
    PROCESSING = "processing" 
    FAILED = "failed"
    DEGRADED = "degraded"


@dataclass
class ProcessingProgress:
    """Progress tracking structure per AC A1.3"""
    timestamp: datetime
    status: str
    component: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class PipelineResults:
    """Unified pipeline results structure per AC A1.6"""
    processed_channels: int
    total_meetings_detected: int
    enhanced_conversations: Dict[str, Any]
    processing_timestamp: datetime
    execution_mode: ExecutionMode
    performance_metrics: Dict[str, Any]
    component_status: Dict[str, ComponentStatus]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['processing_timestamp'] = self.processing_timestamp.isoformat()
        result['execution_mode'] = self.execution_mode.value
        result['component_status'] = {k: v.value for k, v in self.component_status.items()}
        return result


class SlackPipelineOrchestrator:
    """
    Basic integration pipeline for Slack-only processing
    Implements Phase 6A acceptance criteria with realistic scope
    """
    
    def __init__(self, base_path: Path, config: Optional[Dict[str, Any]] = None):
        self.base_path = Path(base_path)
        self.config = config or self._get_default_config()
        
        # Initialize components (sequential processing per AC A1.4)
        self.slack_collector = SlackCollector()
        self.slack_intelligence = SlackIntelligence(self.slack_collector)
        self.slack_extractor = SlackStructuredExtractor()
        self.state_manager = SlackStateManager(self.base_path)
        
        # Component status tracking for isolation per AC C1
        self.component_status = {
            'slack_collection': ComponentStatus.HEALTHY,
            'slack_intelligence': ComponentStatus.HEALTHY,
            'results_aggregation': ComponentStatus.HEALTHY,
            'monitoring': ComponentStatus.HEALTHY
        }
        
        # Progress tracking per AC A1.3
        self.progress_callbacks: List[Callable[[ProcessingProgress], None]] = []
        self.processing_history: List[ProcessingProgress] = []
        
        # Performance metrics per AC B1
        self.performance_metrics = {
            'start_time': None,
            'end_time': None,
            'memory_usage_mb': 0,
            'channels_processed': 0,
            'messages_processed': 0,
            'meetings_detected': 0,
            'error_count': 0
        }
        
        print(f"🚀 Slack Pipeline Orchestrator initialized")
        print(f"💾 Base path: {self.base_path}")
        print(f"🔧 Execution modes: {[mode.value for mode in ExecutionMode]}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration for pipeline"""
        return {
            'max_channels': 100,
            'batch_size': 50,
            'enable_checkpoints': True,
            'checkpoint_interval_seconds': 300,  # 5 minutes
            'enable_monitoring': True,
            'performance_targets': {
                'max_memory_mb': 1024,  # 1GB per revised targets
                'max_response_time_seconds': 2.0,
                'min_intelligence_accuracy': 0.80
            }
        }
    
    def add_progress_callback(self, callback: Callable[[ProcessingProgress], None]):
        """Add progress tracking callback per AC A1.3"""
        self.progress_callbacks.append(callback)
    
    def _track_progress(self, status: str, component: str, details: Dict[str, Any]):
        """Track and notify progress"""
        progress = ProcessingProgress(
            timestamp=datetime.now(timezone.utc),
            status=status,
            component=component,
            details=details
        )
        
        self.processing_history.append(progress)
        
        # Notify callbacks
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def execute_pipeline(self, 
                        execution_mode: ExecutionMode = ExecutionMode.INCREMENTAL,
                        max_channels: Optional[int] = None) -> PipelineResults:
        """
        Execute single command Slack pipeline per AC A1.1
        Sequential processing per AC A1.4
        """
        start_time = time.time()
        self.performance_metrics['start_time'] = start_time
        
        print(f"\n🚀 EXECUTING SLACK PIPELINE")
        print(f"📋 Mode: {execution_mode.value}")
        print(f"🎯 Max channels: {max_channels or self.config['max_channels']}")
        
        self._track_progress('started', 'pipeline', {
            'execution_mode': execution_mode.value,
            'max_channels': max_channels or self.config['max_channels']
        })
        
        try:
            # Step 1: Slack Collection (with component isolation)
            collection_results = self._execute_slack_collection(execution_mode, max_channels)
            
            # Step 2: Intelligence Enhancement (sequential processing)
            intelligence_results = self._execute_slack_intelligence(collection_results)
            
            # Step 3: Results Aggregation 
            aggregated_results = self._execute_results_aggregation(intelligence_results)
            
            # Calculate final performance metrics
            end_time = time.time()
            self.performance_metrics.update({
                'end_time': end_time,
                'total_processing_time': end_time - start_time,
                'throughput_channels_per_second': aggregated_results['processed_channels'] / (end_time - start_time)
            })
            
            # Create pipeline results per AC A1.6
            results = PipelineResults(
                processed_channels=aggregated_results['processed_channels'],
                total_meetings_detected=aggregated_results['total_meetings_detected'],
                enhanced_conversations=aggregated_results['enhanced_conversations'],
                processing_timestamp=datetime.now(timezone.utc),
                execution_mode=execution_mode,
                performance_metrics=self.performance_metrics,
                component_status=self.component_status
            )
            
            self._track_progress('completed', 'pipeline', {
                'processed_channels': results.processed_channels,
                'meetings_detected': results.total_meetings_detected,
                'processing_time': self.performance_metrics['total_processing_time']
            })
            
            print(f"✅ PIPELINE COMPLETED")
            print(f"📊 Processed: {results.processed_channels} channels")
            print(f"🎯 Detected: {results.total_meetings_detected} meetings")
            print(f"⏱️ Time: {self.performance_metrics['total_processing_time']:.2f}s")
            
            return results
            
        except Exception as e:
            self.performance_metrics['error_count'] += 1
            self._track_progress('error', 'pipeline', {'error': str(e)})
            logger.error(f"Pipeline execution failed: {e}")
            
            # Return partial results with error status per AC C2
            return self._create_error_results(str(e), execution_mode)
    
    def _execute_slack_collection(self, 
                                 execution_mode: ExecutionMode,
                                 max_channels: Optional[int]) -> Dict[str, Any]:
        """Execute Slack collection component with isolation per AC C1"""
        component = 'slack_collection'
        
        try:
            self.component_status[component] = ComponentStatus.PROCESSING
            self._track_progress('processing', component, {'stage': 'started'})
            
            # Determine if force refresh is needed
            force_refresh = execution_mode == ExecutionMode.FULL_REFRESH
            
            # Execute collection
            collection_results = self.slack_collector.collect_all_slack_data(
                force_refresh=force_refresh,
                max_channels=max_channels or self.config['max_channels']
            )
            
            self.component_status[component] = ComponentStatus.HEALTHY
            self.performance_metrics['channels_processed'] = collection_results.get('channel_results', {}).get('successful_collections', 0)
            
            self._track_progress('completed', component, {
                'channels_collected': collection_results.get('channel_results', {}).get('successful_collections', 0),
                'total_messages': collection_results.get('channel_results', {}).get('total_messages_collected', 0)
            })
            
            return collection_results
            
        except Exception as e:
            self.component_status[component] = ComponentStatus.FAILED
            logger.error(f"Slack collection failed: {e}")
            
            # Component isolation - return empty results to allow other components to continue
            return {
                'channel_results': {'successful_collections': 0, 'total_messages_collected': 0},
                'collected_data': {}
            }
    
    def _execute_slack_intelligence(self, collection_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Slack intelligence enhancement with error handling per AC C3"""
        component = 'slack_intelligence'
        
        try:
            self.component_status[component] = ComponentStatus.PROCESSING
            self._track_progress('processing', component, {'stage': 'analyzing_conversations'})
            
            collected_data = collection_results.get('collected_data', {})
            enhanced_conversations = {}
            
            for channel_id, conversation_data in collected_data.items():
                try:
                    # Apply intelligence enhancement
                    enhanced_data = self.slack_intelligence.enhance_conversation_analytics(conversation_data)
                    enhanced_conversations[channel_id] = enhanced_data
                    
                except Exception as e:
                    logger.warning(f"Intelligence enhancement failed for {channel_id}: {e}")
                    # Graceful degradation - include original data
                    enhanced_conversations[channel_id] = conversation_data
            
            self.component_status[component] = ComponentStatus.HEALTHY
            self.performance_metrics['messages_processed'] = sum(
                len(conv.get('messages', [])) for conv in enhanced_conversations.values()
            )
            
            self._track_progress('completed', component, {
                'channels_enhanced': len(enhanced_conversations),
                'intelligence_applied': True
            })
            
            return {
                'enhanced_conversations': enhanced_conversations,
                'original_collection_results': collection_results
            }
            
        except Exception as e:
            self.component_status[component] = ComponentStatus.FAILED
            logger.error(f"Slack intelligence failed: {e}")
            
            # Component isolation - return original data without enhancement
            return {
                'enhanced_conversations': collection_results.get('collected_data', {}),
                'original_collection_results': collection_results
            }
    
    def _execute_results_aggregation(self, intelligence_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute results aggregation with coordination metrics per AC A1.6"""
        component = 'results_aggregation'
        
        try:
            self.component_status[component] = ComponentStatus.PROCESSING
            self._track_progress('processing', component, {'stage': 'aggregating_results'})
            
            enhanced_conversations = intelligence_results.get('enhanced_conversations', {})
            
            # Calculate coordination metrics
            total_meetings_detected = 0
            coordination_metrics = {}
            
            for channel_id, conversation in enhanced_conversations.items():
                # Count meeting intents
                meeting_intents = len(conversation.get('meeting_intents', []))
                total_meetings_detected += meeting_intents
                
                # Extract coordination metrics
                analytics = conversation.get('analytics', {})
                meeting_intel = analytics.get('meeting_intelligence', {})
                
                coordination_metrics[channel_id] = {
                    'meeting_intents_detected': meeting_intents,
                    'scheduling_conversations': meeting_intel.get('scheduling_conversations', 0),
                    'meeting_density': meeting_intel.get('meeting_density', 0.0),
                    'coordination_score': meeting_intel.get('conversation_context', {}).get('scheduling_density', 0.0)
                }
            
            self.component_status[component] = ComponentStatus.HEALTHY
            self.performance_metrics['meetings_detected'] = total_meetings_detected
            
            aggregated_results = {
                'processed_channels': len(enhanced_conversations),
                'total_meetings_detected': total_meetings_detected,
                'enhanced_conversations': enhanced_conversations,
                'coordination_metrics': coordination_metrics,
                'aggregation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._track_progress('completed', component, {
                'aggregated_channels': len(enhanced_conversations),
                'total_meetings': total_meetings_detected,
                'coordination_metrics_calculated': True
            })
            
            return aggregated_results
            
        except Exception as e:
            self.component_status[component] = ComponentStatus.FAILED
            logger.error(f"Results aggregation failed: {e}")
            
            # Component isolation - return minimal results
            enhanced_conversations = intelligence_results.get('enhanced_conversations', {})
            return {
                'processed_channels': len(enhanced_conversations),
                'total_meetings_detected': 0,
                'enhanced_conversations': enhanced_conversations,
                'coordination_metrics': {},
                'aggregation_timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _create_error_results(self, error_message: str, execution_mode: ExecutionMode) -> PipelineResults:
        """Create error results with partial success per AC C2"""
        return PipelineResults(
            processed_channels=0,
            total_meetings_detected=0,
            enhanced_conversations={},
            processing_timestamp=datetime.now(timezone.utc),
            execution_mode=execution_mode,
            performance_metrics=self.performance_metrics,
            component_status=self.component_status
        )
    
    def get_component_health(self) -> Dict[str, Any]:
        """Get component health status for monitoring per AC B2"""
        return {
            'component_status': {k: v.value for k, v in self.component_status.items()},
            'overall_health': 'healthy' if all(s == ComponentStatus.HEALTHY for s in self.component_status.values()) else 'degraded',
            'failed_components': [k for k, v in self.component_status.items() if v == ComponentStatus.FAILED],
            'healthy_components': [k for k, v in self.component_status.items() if v == ComponentStatus.HEALTHY],
            'isolation_success_rate': len([s for s in self.component_status.values() if s == ComponentStatus.HEALTHY]) / len(self.component_status)
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for baseline measurement per AC B1"""
        import psutil
        import os
        
        current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        self.performance_metrics['current_memory_mb'] = current_memory
        
        return {
            'processing_metrics': self.performance_metrics.copy(),
            'component_health': self.get_component_health(),
            'targets_met': {
                'memory_under_1gb': current_memory < 1024,
                'response_time_under_2s': self.performance_metrics.get('total_processing_time', 0) < 2.0 if self.performance_metrics.get('total_processing_time') else None,
                'channels_processed': self.performance_metrics.get('channels_processed', 0)
            }
        }
    
    def export_results(self, results: PipelineResults, format_type: str = 'json', output_path: Optional[Path] = None) -> Path:
        """Export pipeline results per integration requirements"""
        if output_path is None:
            output_path = self.base_path / "data" / "results" / f"slack_pipeline_{int(time.time())}.{format_type}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format_type == 'json':
            with open(output_path, 'w') as f:
                json.dump(results.to_dict(), f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        print(f"💾 Results exported to: {output_path}")
        return output_path


# Command-line interface for single command execution per AC A1.1
def main():
    """Command-line interface for Phase 6 pipeline execution"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Execute Slack Pipeline - Phase 6 Integration')
    parser.add_argument('--mode', choices=['incremental', 'full_refresh'], default='incremental',
                       help='Execution mode (default: incremental)')
    parser.add_argument('--max-channels', type=int, default=100,
                       help='Maximum channels to process (default: 100)')
    parser.add_argument('--base-path', type=Path, default=Path.cwd(),
                       help='Base path for data storage')
    parser.add_argument('--export-format', choices=['json'], default='json',
                       help='Export format (default: json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    
    try:
        # Initialize orchestrator
        orchestrator = SlackPipelineOrchestrator(args.base_path)
        
        # Add progress callback for CLI output
        def progress_callback(progress: ProcessingProgress):
            print(f"📊 {progress.status.upper()}: {progress.component} - {progress.details}")
        
        orchestrator.add_progress_callback(progress_callback)
        
        # Execute pipeline
        execution_mode = ExecutionMode.INCREMENTAL if args.mode == 'incremental' else ExecutionMode.FULL_REFRESH
        
        print("🚀 Starting Slack Pipeline Execution...")
        results = orchestrator.execute_pipeline(
            execution_mode=execution_mode,
            max_channels=args.max_channels
        )
        
        # Export results
        export_path = orchestrator.export_results(results, args.export_format)
        
        # Display summary
        print("\n📋 PIPELINE SUMMARY")
        print(f"📊 Channels processed: {results.processed_channels}")
        print(f"🎯 Meetings detected: {results.total_meetings_detected}")
        print(f"⏱️ Processing time: {orchestrator.performance_metrics.get('total_processing_time', 0):.2f}s")
        print(f"💾 Results exported: {export_path}")
        
        # Display component health
        health = orchestrator.get_component_health()
        print(f"🏥 System health: {health['overall_health']}")
        if health['failed_components']:
            print(f"❌ Failed components: {', '.join(health['failed_components'])}")
        
        return 0 if health['overall_health'] == 'healthy' else 1
        
    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())