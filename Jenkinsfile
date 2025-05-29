// Jenkinsfile

pipeline {
    agent 50000

    environment {
        COMPOSE_FILE = 'docker-compose.prod.yaml'
        GITHUB_REPO_URL = 'https://github.com/damvantage/vantage-document-parser.git'
        GITHUB_BRANCH = 'main'
    }

    stages {
        stage('Checkout Source Code') {
            steps {
                git branch: env.GITHUB_BRANCH, url: env.GITHUB_REPO_URL
            }
        }

        stage('Build Docker Images') {
            steps {
                sh 'make build-prod'
            }
        }

        stage('Wait for Services') {
            steps {
                sh 'make up-prod'
                script {
                    sleep 30
                }
                sh 'make healthcheck-prod'
            }
        }

        stage('Run Database Migrations') {
            steps {
                sh 'make db-upgrade-prod'
            }
        }

        stage('Deploy Application') {
            steps {
                sh 'make deploy-prod'
            }
        }

        stage('Health Check Application') {
            steps {
                script {
                    sleep 10
                }
                sh 'make healthcheck-prod'
            }
        }
    }

    // Phần post-build actions, chạy sau khi tất cả các stage hoàn thành.
    post {
        success {
            echo '🚀 Triển khai thành công!'
        }
        failure {
            echo '❌ Triển khai thất bại! Vui lòng kiểm tra logs.'
        }
        always {
            echo 'Pipeline đã hoàn thành.'
        }
    }
}
