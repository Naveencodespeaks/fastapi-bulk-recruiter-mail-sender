pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv ci-env
                    ci-env/bin/pip install --upgrade pip
                    ci-env/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    ci-env/bin/python -m pytest
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build -t sainaveenadep/bulk-mail-sender:latest .
                '''
            }
        }
    }

    post {
        success {
            echo 'CI pipeline completed successfully!'
        }

        failure {
            echo 'CI pipeline failed. Check the stage logs.'
        }
    }
}
