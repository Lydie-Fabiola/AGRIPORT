"""
Health check services for Farm2Market.
"""
import time
import redis
from django.db import connection, connections
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views import View
from celery import current_app as celery_app
import requests


class HealthCheckService:
    """
    Service for performing health checks on various system components.
    """
    
    def __init__(self):
        self.checks = {
            'database': self.check_database,
            'redis': self.check_redis,
            'cache': self.check_cache,
            'celery': self.check_celery,
            'storage': self.check_storage,
            'external_services': self.check_external_services,
        }
    
    def run_all_checks(self):
        """Run all health checks and return results."""
        results = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {},
            'summary': {
                'total': len(self.checks),
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        
        overall_healthy = True
        
        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                check_result = check_func()
                duration = time.time() - start_time
                
                check_result['duration_ms'] = round(duration * 1000, 2)
                results['checks'][check_name] = check_result
                
                if check_result['status'] == 'healthy':
                    results['summary']['passed'] += 1
                elif check_result['status'] == 'warning':
                    results['summary']['warnings'] += 1
                else:
                    results['summary']['failed'] += 1
                    overall_healthy = False
                    
            except Exception as e:
                results['checks'][check_name] = {
                    'status': 'unhealthy',
                    'message': f'Health check failed: {str(e)}',
                    'error': str(e)
                }
                results['summary']['failed'] += 1
                overall_healthy = False
        
        if not overall_healthy:
            results['status'] = 'unhealthy'
        elif results['summary']['warnings'] > 0:
            results['status'] = 'degraded'
        
        return results
    
    def check_database(self):
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Test primary database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            query_time = time.time() - start_time
            
            # Check all database connections
            db_status = {}
            for alias in connections:
                try:
                    conn = connections[alias]
                    conn.ensure_connection()
                    db_status[alias] = {
                        'status': 'connected',
                        'vendor': conn.vendor,
                        'is_usable': conn.is_usable()
                    }
                except Exception as e:
                    db_status[alias] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Determine overall status
            if query_time > 1.0:
                status = 'warning'
                message = f'Database responding slowly ({query_time:.2f}s)'
            else:
                status = 'healthy'
                message = 'Database is healthy'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'query_time_ms': round(query_time * 1000, 2),
                    'connections': db_status
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}',
                'error': str(e)
            }
    
    def check_redis(self):
        """Check Redis connectivity and performance."""
        try:
            # Get Redis connection from Django cache
            redis_client = cache._cache.get_client()
            
            start_time = time.time()
            
            # Test basic operations
            test_key = 'health_check_test'
            redis_client.set(test_key, 'test_value', ex=10)
            value = redis_client.get(test_key)
            redis_client.delete(test_key)
            
            operation_time = time.time() - start_time
            
            # Get Redis info
            redis_info = redis_client.info()
            
            # Check memory usage
            used_memory = redis_info.get('used_memory', 0)
            max_memory = redis_info.get('maxmemory', 0)
            
            memory_usage_percent = 0
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
            
            # Determine status
            if operation_time > 0.1:
                status = 'warning'
                message = f'Redis responding slowly ({operation_time:.3f}s)'
            elif memory_usage_percent > 90:
                status = 'warning'
                message = f'Redis memory usage high ({memory_usage_percent:.1f}%)'
            else:
                status = 'healthy'
                message = 'Redis is healthy'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'operation_time_ms': round(operation_time * 1000, 2),
                    'memory_usage_percent': round(memory_usage_percent, 1),
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'version': redis_info.get('redis_version', 'unknown')
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}',
                'error': str(e)
            }
    
    def check_cache(self):
        """Check Django cache functionality."""
        try:
            start_time = time.time()
            
            # Test cache operations
            test_key = 'health_check_cache_test'
            test_value = {'timestamp': timezone.now().isoformat()}
            
            cache.set(test_key, test_value, 10)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            
            operation_time = time.time() - start_time
            
            if cached_value != test_value:
                return {
                    'status': 'unhealthy',
                    'message': 'Cache value mismatch',
                    'error': 'Retrieved value does not match stored value'
                }
            
            # Determine status
            if operation_time > 0.1:
                status = 'warning'
                message = f'Cache responding slowly ({operation_time:.3f}s)'
            else:
                status = 'healthy'
                message = 'Cache is healthy'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'operation_time_ms': round(operation_time * 1000, 2),
                    'backend': cache.__class__.__name__
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Cache operation failed: {str(e)}',
                'error': str(e)
            }
    
    def check_celery(self):
        """Check Celery worker status."""
        try:
            # Get active workers
            inspect = celery_app.control.inspect()
            
            start_time = time.time()
            active_workers = inspect.active()
            stats = inspect.stats()
            check_time = time.time() - start_time
            
            if not active_workers:
                return {
                    'status': 'unhealthy',
                    'message': 'No active Celery workers found',
                    'details': {
                        'active_workers': 0,
                        'check_time_ms': round(check_time * 1000, 2)
                    }
                }
            
            worker_count = len(active_workers)
            
            # Check worker health
            unhealthy_workers = []
            for worker_name, worker_stats in (stats or {}).items():
                if not worker_stats:
                    unhealthy_workers.append(worker_name)
            
            # Determine status
            if unhealthy_workers:
                status = 'warning'
                message = f'{len(unhealthy_workers)} workers unhealthy'
            elif check_time > 2.0:
                status = 'warning'
                message = f'Celery responding slowly ({check_time:.2f}s)'
            else:
                status = 'healthy'
                message = f'{worker_count} workers active'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'active_workers': worker_count,
                    'unhealthy_workers': unhealthy_workers,
                    'check_time_ms': round(check_time * 1000, 2)
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Celery check failed: {str(e)}',
                'error': str(e)
            }
    
    def check_storage(self):
        """Check file storage accessibility."""
        try:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            start_time = time.time()
            
            # Test file operations
            test_filename = f'health_check_{int(time.time())}.txt'
            test_content = ContentFile(b'health check test')
            
            # Save file
            saved_name = default_storage.save(test_filename, test_content)
            
            # Check if file exists
            exists = default_storage.exists(saved_name)
            
            # Read file
            if exists:
                with default_storage.open(saved_name, 'rb') as f:
                    content = f.read()
            
            # Clean up
            if exists:
                default_storage.delete(saved_name)
            
            operation_time = time.time() - start_time
            
            if not exists:
                return {
                    'status': 'unhealthy',
                    'message': 'File storage write/read failed',
                    'error': 'File was not found after saving'
                }
            
            # Determine status
            if operation_time > 1.0:
                status = 'warning'
                message = f'Storage responding slowly ({operation_time:.2f}s)'
            else:
                status = 'healthy'
                message = 'Storage is healthy'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'operation_time_ms': round(operation_time * 1000, 2),
                    'storage_backend': default_storage.__class__.__name__
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Storage check failed: {str(e)}',
                'error': str(e)
            }
    
    def check_external_services(self):
        """Check external service connectivity."""
        external_services = getattr(settings, 'EXTERNAL_SERVICES_HEALTH_CHECK', {})
        
        if not external_services:
            return {
                'status': 'healthy',
                'message': 'No external services configured',
                'details': {}
            }
        
        service_results = {}
        overall_healthy = True
        
        for service_name, service_config in external_services.items():
            try:
                start_time = time.time()
                
                response = requests.get(
                    service_config['url'],
                    timeout=service_config.get('timeout', 5),
                    headers=service_config.get('headers', {})
                )
                
                check_time = time.time() - start_time
                
                if response.status_code == 200:
                    service_results[service_name] = {
                        'status': 'healthy',
                        'response_time_ms': round(check_time * 1000, 2),
                        'status_code': response.status_code
                    }
                else:
                    service_results[service_name] = {
                        'status': 'unhealthy',
                        'response_time_ms': round(check_time * 1000, 2),
                        'status_code': response.status_code
                    }
                    overall_healthy = False
                    
            except Exception as e:
                service_results[service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                overall_healthy = False
        
        return {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'message': f'Checked {len(external_services)} external services',
            'details': service_results
        }


class HealthCheckView(View):
    """
    HTTP endpoint for health checks.
    """
    
    def __init__(self):
        super().__init__()
        self.health_service = HealthCheckService()
    
    def get(self, request):
        """Return health check results."""
        # Check if this is a detailed health check
        detailed = request.GET.get('detailed', 'false').lower() == 'true'
        
        if detailed:
            results = self.health_service.run_all_checks()
        else:
            # Quick health check - just database and cache
            results = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'checks': {
                    'database': self.health_service.check_database(),
                    'cache': self.health_service.check_cache()
                }
            }
            
            # Determine overall status
            if any(check['status'] == 'unhealthy' for check in results['checks'].values()):
                results['status'] = 'unhealthy'
            elif any(check['status'] == 'warning' for check in results['checks'].values()):
                results['status'] = 'degraded'
        
        # Return appropriate HTTP status code
        if results['status'] == 'healthy':
            status_code = 200
        elif results['status'] == 'degraded':
            status_code = 200  # Still operational
        else:
            status_code = 503  # Service unavailable
        
        return JsonResponse(results, status=status_code)


class ReadinessCheckView(View):
    """
    Readiness check for Kubernetes/container orchestration.
    """
    
    def get(self, request):
        """Check if application is ready to serve requests."""
        health_service = HealthCheckService()
        
        # Check critical components only
        critical_checks = {
            'database': health_service.check_database(),
            'cache': health_service.check_cache()
        }
        
        # Application is ready if critical components are healthy
        ready = all(
            check['status'] in ['healthy', 'warning'] 
            for check in critical_checks.values()
        )
        
        results = {
            'ready': ready,
            'timestamp': timezone.now().isoformat(),
            'checks': critical_checks
        }
        
        return JsonResponse(results, status=200 if ready else 503)


class LivenessCheckView(View):
    """
    Liveness check for Kubernetes/container orchestration.
    """
    
    def get(self, request):
        """Check if application is alive and responding."""
        # Simple liveness check - just return 200 if Django is running
        return JsonResponse({
            'alive': True,
            'timestamp': timezone.now().isoformat(),
            'version': getattr(settings, 'VERSION', 'unknown')
        })
