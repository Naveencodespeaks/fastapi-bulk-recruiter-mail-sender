
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'sainaveenadep/cold-email-python'
        IMAGE_TAG  = "${BUILD_NUMBER}"
        CONTAINER  = 'bulk-recruiter'
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

        stage('Push Docker Image') {
            steps {
                echo '📤 Pushing Docker image to Docker Hub...'

                withCredentials([
                    usernamePassword(
                        credentialsId: 'ec609db9-c343-4264-ad15-0c5e3a9c8e2c',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {
                    sh '''
                        echo "$DOCKER_PASSWORD" | docker login \
                            -u "$DOCKER_USERNAME" \
                            --password-stdin

                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_NAME}:latest

                        docker logout
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                echo '🚀 Deploying application...'

                sh '''
                    docker compose pull
                    docker compose up -d --force-recreate
                '''
            }
        }

        stage('Health Check') {
            steps {
                echo '❤️ Checking application health...'

                sh '''
                    sleep 10

                    curl --fail http://localhost:8000/ || exit 1

                    echo "✅ Application is healthy!"
                '''
            }
        }
    }

    post {

        success {
            echo '🎉 CI/CD pipeline completed successfully!'
            echo '🚀 FastAPI application has been deployed.'
        }

        failure {
            echo '❌ Pipeline failed.'
            echo 'Check the Jenkins console output for details.'
        }

        always {
            echo '🧹 Cleaning Jenkins workspace...'
            cleanWs()
        }
    }
}

