```groovy
pipeline {
    agent any

    environment {
        AWS_REGION  = 'ap-south-2'
        AWS_ACCOUNT = '280710007209'

        ECR_REPO    = 'cold-email-python'
        ECR_REGISTRY = "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

        IMAGE_NAME  = "${ECR_REGISTRY}/${ECR_REPO}"
        IMAGE_TAG   = "${BUILD_NUMBER}"

        CONTAINER   = 'bulk-recruiter'
    }

    stages {

        stage('Checkout') {
            steps {
                echo '📥 Checking out source code...'

                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '📦 Installing Python dependencies...'

                sh '''
                    python3 -m venv venv
                    . venv/bin/activate

                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo '🧪 Running tests...'

                sh '''
                    . venv/bin/activate

                    pytest -v
                '''
            }
        }

        stage('Login to AWS ECR') {
            steps {
                echo '🔐 Logging into AWS ECR...'

                sh '''
                    aws ecr get-login-password \
                        --region ${AWS_REGION} | \
                    docker login \
                        --username AWS \
                        --password-stdin ${ECR_REGISTRY}
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo '🐳 Building Docker image...'

                sh '''
                    docker build \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:latest \
                        .
                '''
            }
        }

        stage('Push Docker Image to ECR') {
            steps {
                echo '📤 Pushing Docker image to AWS ECR...'

                sh '''
                    docker push ${IMAGE_NAME}:${IMAGE_TAG}
                    docker push ${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Deploy') {
            steps {
                echo '🚀 Deploying application...'

                withCredentials([
                    file(
                        credentialsId: 'env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    sh '''
                        echo "📄 Loading environment configuration..."

                        cp "$ENV_FILE" .env

                        echo "🐳 Pulling ECR image..."

                        docker compose pull

                        echo "🧹 Removing existing container if present..."

                        docker rm -f "${CONTAINER}" 2>/dev/null || true

                        echo "🚀 Starting application..."

                        docker compose up -d --force-recreate

                        echo "✅ Application deployment completed."
                    '''
                }
            }
        }

        stage('Health Check') {
            steps {
                echo '❤️ Checking application health...'

                sh '''
                    echo "⏳ Waiting for application to start..."

                    sleep 10

                    echo "🔍 Checking http://localhost:8000/ ..."

                    curl --fail --silent --show-error \
                        http://localhost:8000/ \
                        || exit 1

                    echo "✅ Application is healthy!"
                '''
            }
        }
    }

    post {

        success {
            echo '🎉 CI/CD pipeline completed successfully!'
            echo '🚀 FastAPI application deployed from AWS ECR.'
        }

        failure {
            echo '❌ CI/CD pipeline failed.'
            echo '🔍 Check the Jenkins console output for the exact error.'
        }

        always {
            echo '🧹 Cleaning Jenkins workspace...'

            cleanWs()
        }
    }
}
```

