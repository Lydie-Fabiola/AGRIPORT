"""
Database optimization services for Farm2Market.
"""
from django.db import connection, connections
from django.db.models import Prefetch, Q
from django.conf import settings
from django.core.management.base import BaseCommand
import time
import logging

logger = logging.getLogger(__name__)


class DatabaseOptimizationService:
    """
    Service for database query optimization and monitoring.
    """
    
    def __init__(self):
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 1.0)  # 1 second
    
    def optimize_queryset(self, queryset, optimization_type='list'):
        """
        Apply common optimizations to querysets.
        """
        model_name = queryset.model.__name__.lower()
        
        if optimization_type == 'list':
            return self._optimize_for_list_view(queryset, model_name)
        elif optimization_type == 'detail':
            return self._optimize_for_detail_view(queryset, model_name)
        elif optimization_type == 'api':
            return self._optimize_for_api_response(queryset, model_name)
        
        return queryset
    
    def _optimize_for_list_view(self, queryset, model_name):
        """Optimize queryset for list views."""
        optimizations = {
            'product': lambda qs: qs.select_related('farmer', 'categories').prefetch_related('images'),
            'order': lambda qs: qs.select_related('buyer', 'farmer', 'delivery_address'),
            'message': lambda qs: qs.select_related('sender', 'recipient', 'conversation'),
            'notification': lambda qs: qs.select_related('recipient'),
            'review': lambda qs: qs.select_related('buyer', 'product__farmer'),
        }
        
        if model_name in optimizations:
            return optimizations[model_name](queryset)
        
        return queryset
    
    def _optimize_for_detail_view(self, queryset, model_name):
        """Optimize queryset for detail views."""
        optimizations = {
            'product': lambda qs: qs.select_related(
                'farmer', 'farmer__farmer_profile'
            ).prefetch_related(
                'images', 'categories', 'reviews__buyer',
                Prefetch('farmer__products', queryset=qs.model.objects.filter(status='Available')[:5])
            ),
            'order': lambda qs: qs.select_related(
                'buyer', 'farmer', 'delivery_address'
            ).prefetch_related(
                'items__product', 'status_history', 'messages'
            ),
            'user': lambda qs: qs.select_related(
                'farmer_profile', 'buyer_preferences'
            ).prefetch_related(
                'products', 'orders_as_buyer', 'orders_as_farmer'
            ),
        }
        
        if model_name in optimizations:
            return optimizations[model_name](queryset)
        
        return queryset
    
    def _optimize_for_api_response(self, queryset, model_name):
        """Optimize queryset for API responses."""
        # Use only() to limit fields for API responses
        api_fields = {
            'product': [
                'id', 'product_name', 'description', 'price', 'quantity',
                'status', 'farmer__id', 'farmer__full_name', 'created_at'
            ],
            'order': [
                'id', 'order_number', 'status', 'total_amount',
                'buyer__id', 'buyer__full_name', 'farmer__id', 'farmer__full_name',
                'created_at', 'updated_at'
            ],
            'user': [
                'id', 'email', 'full_name', 'user_type', 'is_active',
                'date_joined', 'last_login'
            ],
        }
        
        if model_name in api_fields:
            return queryset.only(*api_fields[model_name])
        
        return queryset
    
    def monitor_query_performance(self, func):
        """
        Decorator to monitor query performance.
        """
        def wrapper(*args, **kwargs):
            # Reset query count
            initial_queries = len(connection.queries)
            start_time = time.time()
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Calculate metrics
            end_time = time.time()
            execution_time = end_time - start_time
            query_count = len(connection.queries) - initial_queries
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected in {func.__name__}: "
                    f"{execution_time:.2f}s, {query_count} queries"
                )
                
                # Log individual slow queries
                for query in connection.queries[initial_queries:]:
                    query_time = float(query['time'])
                    if query_time > 0.1:  # 100ms threshold
                        logger.warning(f"Slow SQL query ({query_time:.2f}s): {query['sql'][:200]}...")
            
            return result
        
        return wrapper
    
    def analyze_query_patterns(self):
        """
        Analyze query patterns for optimization opportunities.
        """
        queries = connection.queries
        
        # Group queries by type
        query_patterns = {}
        
        for query in queries:
            sql = query['sql']
            query_type = sql.split()[0].upper()
            
            if query_type not in query_patterns:
                query_patterns[query_type] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'max_time': 0
                }
            
            query_time = float(query['time'])
            query_patterns[query_type]['count'] += 1
            query_patterns[query_type]['total_time'] += query_time
            query_patterns[query_type]['max_time'] = max(
                query_patterns[query_type]['max_time'], query_time
            )
        
        # Calculate averages
        for pattern in query_patterns.values():
            if pattern['count'] > 0:
                pattern['avg_time'] = pattern['total_time'] / pattern['count']
        
        return query_patterns


class ConnectionPoolService:
    """
    Service for managing database connection pooling.
    """
    
    def __init__(self):
        self.pool_settings = {
            'max_connections': getattr(settings, 'DB_MAX_CONNECTIONS', 20),
            'min_connections': getattr(settings, 'DB_MIN_CONNECTIONS', 5),
            'connection_timeout': getattr(settings, 'DB_CONNECTION_TIMEOUT', 30),
        }
    
    def get_connection_stats(self):
        """
        Get database connection statistics.
        """
        stats = {}
        
        for alias in connections:
            connection = connections[alias]
            
            stats[alias] = {
                'vendor': connection.vendor,
                'is_usable': connection.is_usable(),
                'queries_count': len(connection.queries),
                'settings': {
                    'name': connection.settings_dict.get('NAME'),
                    'host': connection.settings_dict.get('HOST'),
                    'port': connection.settings_dict.get('PORT'),
                }
            }
        
        return stats
    
    def close_old_connections(self):
        """
        Close old database connections.
        """
        for alias in connections:
            connections[alias].close_if_unusable_or_obsolete()


class QueryOptimizer:
    """
    Query optimization utilities.
    """
    
    @staticmethod
    def optimize_product_queries():
        """
        Optimize common product queries.
        """
        from apps.products.models import Product
        
        # Optimized product list query
        def get_products_optimized(filters=None):
            queryset = Product.objects.select_related(
                'farmer', 'farmer__farmer_profile'
            ).prefetch_related(
                'categories', 'images'
            ).filter(status='Available')
            
            if filters:
                if 'category' in filters:
                    queryset = queryset.filter(categories__id=filters['category'])
                if 'price_min' in filters:
                    queryset = queryset.filter(price__gte=filters['price_min'])
                if 'price_max' in filters:
                    queryset = queryset.filter(price__lte=filters['price_max'])
                if 'location' in filters:
                    queryset = queryset.filter(
                        farmer__farmer_profile__location__icontains=filters['location']
                    )
            
            return queryset
        
        return get_products_optimized
    
    @staticmethod
    def optimize_order_queries():
        """
        Optimize common order queries.
        """
        from apps.orders.models import Order
        
        def get_orders_optimized(user, user_type='buyer'):
            queryset = Order.objects.select_related(
                'buyer', 'farmer', 'delivery_address'
            ).prefetch_related(
                'items__product', 'status_history'
            )
            
            if user_type == 'buyer':
                queryset = queryset.filter(buyer=user)
            elif user_type == 'farmer':
                queryset = queryset.filter(farmer=user)
            
            return queryset.order_by('-created_at')
        
        return get_orders_optimized
    
    @staticmethod
    def optimize_search_queries():
        """
        Optimize search queries.
        """
        from apps.products.models import Product
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
        
        def search_products_optimized(query, filters=None):
            # Use PostgreSQL full-text search if available
            if hasattr(Product.objects, 'annotate'):
                search_vector = SearchVector('product_name', weight='A') + \
                               SearchVector('description', weight='B')
                search_query = SearchQuery(query)
                
                queryset = Product.objects.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query)
                ).filter(
                    search=search_query,
                    status='Available'
                ).select_related(
                    'farmer'
                ).prefetch_related(
                    'categories', 'images'
                ).order_by('-rank', '-created_at')
            else:
                # Fallback to icontains search
                queryset = Product.objects.filter(
                    Q(product_name__icontains=query) |
                    Q(description__icontains=query),
                    status='Available'
                ).select_related(
                    'farmer'
                ).prefetch_related(
                    'categories', 'images'
                ).order_by('-created_at')
            
            # Apply filters
            if filters:
                if 'category' in filters:
                    queryset = queryset.filter(categories__id=filters['category'])
                if 'price_min' in filters:
                    queryset = queryset.filter(price__gte=filters['price_min'])
                if 'price_max' in filters:
                    queryset = queryset.filter(price__lte=filters['price_max'])
            
            return queryset
        
        return search_products_optimized


class IndexOptimizationService:
    """
    Service for database index optimization.
    """
    
    def __init__(self):
        self.recommended_indexes = {
            'products_product': [
                ['farmer_id', 'status'],
                ['status', 'created_at'],
                ['price', 'status'],
                ['product_name', 'status'],  # For search
            ],
            'orders_order': [
                ['buyer_id', 'status'],
                ['farmer_id', 'status'],
                ['status', 'created_at'],
                ['order_number'],
            ],
            'messaging_message': [
                ['conversation_id', 'timestamp'],
                ['sender_id', 'timestamp'],
                ['recipient_id', 'is_read'],
            ],
            'analytics_useractivity': [
                ['user_id', 'timestamp'],
                ['activity_type', 'timestamp'],
                ['resource_type', 'resource_id'],
            ],
        }
    
    def generate_index_sql(self):
        """
        Generate SQL for creating recommended indexes.
        """
        sql_statements = []
        
        for table, indexes in self.recommended_indexes.items():
            for index_columns in indexes:
                index_name = f"idx_{table}_{'_'.join(index_columns)}"
                columns_str = ', '.join(index_columns)
                
                sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} ({columns_str});"
                sql_statements.append(sql)
        
        return sql_statements
    
    def analyze_missing_indexes(self):
        """
        Analyze queries to identify missing indexes.
        """
        # This would analyze slow query logs and suggest indexes
        # Implementation would depend on database backend
        pass


class DatabaseMaintenanceService:
    """
    Service for database maintenance tasks.
    """
    
    def vacuum_analyze_tables(self):
        """
        Run VACUUM ANALYZE on all tables (PostgreSQL).
        """
        with connection.cursor() as cursor:
            cursor.execute("VACUUM ANALYZE;")
    
    def update_table_statistics(self):
        """
        Update table statistics for query optimization.
        """
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE;")
    
    def check_database_size(self):
        """
        Check database size and table sizes.
        """
        with connection.cursor() as cursor:
            # PostgreSQL specific query
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """)
            
            return cursor.fetchall()
    
    def cleanup_old_data(self):
        """
        Clean up old data to maintain performance.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Clean up old analytics data (keep 1 year)
        cutoff_date = timezone.now() - timedelta(days=365)
        
        from apps.analytics.models import UserActivity, ProductView, SearchAnalytics
        
        # Delete old user activities
        deleted_activities = UserActivity.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        # Delete old product views
        deleted_views = ProductView.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        # Delete old search analytics
        deleted_searches = SearchAnalytics.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        return {
            'deleted_activities': deleted_activities,
            'deleted_views': deleted_views,
            'deleted_searches': deleted_searches,
        }
