"""
Lambda function to initialize pgvector extension and create embeddings table.

This function is invoked once during Terraform deployment to:
1. Create the pgvector extension
2. Create the embeddings table with HNSW index
3. Configure optimal index parameters
"""

import psycopg2
import boto3
import json
import os


def handler(event, context):
    """Initialize pgvector extension and create embeddings table."""
    secret_arn = os.environ['DB_SECRET_ARN']
    db_endpoint = os.environ['DB_CLUSTER_ENDPOINT']
    db_name = os.environ['DB_NAME']
    embedding_dimension = int(os.environ.get('EMBEDDING_DIMENSION', '1536'))

    try:
        # Retrieve credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        secret = secrets_client.get_secret_value(SecretId=secret_arn)
        creds = json.loads(secret['SecretString'])

        # Connect to database
        conn = psycopg2.connect(
            host=db_endpoint,
            port=5432,
            database=db_name,
            user=creds['username'],
            password=creds['password'],
            connect_timeout=10
        )

        cursor = conn.cursor()

        # Create pgvector extension
        print("Creating pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Create embeddings table with HNSW index
        print(f"Creating embeddings table with dimension {embedding_dimension}...")
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                vector_id VARCHAR(255) UNIQUE NOT NULL,
                embedding vector({embedding_dimension}),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Create HNSW index for fast similarity search
        print("Creating HNSW index...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx
            ON embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

        # Create additional indexes for metadata queries
        print("Creating metadata indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_metadata_idx
            ON embeddings USING GIN (metadata);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_created_at_idx
            ON embeddings (created_at DESC);
        """)

        # Commit changes
        conn.commit()
        print("Successfully initialized pgvector extension and tables")

        # Get table info
        cursor.execute("""
            SELECT
                table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'embeddings';
        """)
        table_info = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'pgvector extension initialized successfully',
                'embedding_dimension': embedding_dimension,
                'table_info': {
                    'name': table_info[0] if table_info else 'embeddings',
                    'size': table_info[1] if table_info else '0 bytes'
                }
            })
        }

    except Exception as e:
        print(f"Error initializing pgvector: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to initialize pgvector extension'
            })
        }
