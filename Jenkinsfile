pipeline {
    agent any

    environment {
        JIRA_EMAIL = credentials('jira-email')
        JIRA_API_TOKEN = credentials('jira-token')
        JENKINS_USER = credentials('jenkins-user')
        JENKINS_API_TOKEN = credentials('jenkins-token')
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    git branch: 'main',
                        url: 'https://github.com/El-Vaibhav/PR_Override.git'
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    sh 'pip3 install requests'
                }
            }
        }

        stage('Run Override Script') {
            steps {
                script {
                    sh 'python3 "Override Insight Engine.py"'
                }
            }
        }
    }

    post {
        failure {
            echo "❌ Pipeline failed. Check logs for more details."
        }
        success {
            echo "✅ Pipeline completed successfully."
        }
    }
}

