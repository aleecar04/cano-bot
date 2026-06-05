pipeline {
    agent any

    parameters {
        string(
            name: 'BRANCH',
            defaultValue: 'main',
            description: 'Rama del repositorio a desplegar'
        )
        booleanParam(
            name: 'DEPLOY_BACKEND',
            defaultValue: true,
            description: 'Recompilar y reiniciar el backend (Docker)'
        )
        booleanParam(
            name: 'DEPLOY_FRONTEND',
            defaultValue: true,
            description: 'Recompilar y publicar el frontend'
        )
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        FRONTEND_DEPLOY_DIR = '/var/www/cano-app'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${params.BRANCH}"]],
                    userRemoteConfigs: scm.userRemoteConfigs,
                    extensions: [[$class: 'CleanBeforeCheckout']]
                ])
                sh 'git rev-parse --short HEAD'
            }
        }

        stage('Backend') {
            when { expression { params.DEPLOY_BACKEND } }
            steps {
                sh 'cp /opt/cano4-secrets/.env .env'
                sh 'docker-compose build backend'
                sh 'docker-compose up -d backend'
                sh '''
                    sleep 5
                    curl -fsS http://localhost:8000/health || (echo "Backend no responde"; exit 1)
                '''
            }
        }

        stage('Frontend install') {
            when { expression { params.DEPLOY_FRONTEND } }
            steps {
                sh 'cp /opt/cano4-secrets/cano-app.env cano-app/.env'
                dir('cano-app') {
                    sh 'npm ci --no-audit --no-fund'
                }
            }
        }

        stage('Frontend build') {
            when { expression { params.DEPLOY_FRONTEND } }
            steps {
                dir('cano-app') {
                    sh 'npx expo export --platform web'
                }
            }
        }

        stage('Frontend deploy') {
            when { expression { params.DEPLOY_FRONTEND } }
            steps {
                sh """
                    sudo rsync -a --delete cano-app/dist/ ${env.FRONTEND_DEPLOY_DIR}/
                    sudo systemctl reload apache2
                """
            }
        }
    }

    post {
        success {
            echo "Despliegue completado. Rama: ${params.BRANCH}"
        }
        failure {
            echo "Despliegue fallido. Rama: ${params.BRANCH}"
        }
        always {
            cleanWs(notFailBuild: true)
        }
    }
}
