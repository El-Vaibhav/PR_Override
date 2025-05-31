pipeline {
    agent any

    environment {
        JIRA_EMAIL = credentials('jira-email')           // Jenkins credential ID for JIRA email
        JIRA_API_TOKEN = credentials('jira-token')       // Jenkins credential ID for JIRA API token
        JENKINS_USER = credentials('jenkins-user')       // Jenkins credential ID for Jenkins username
        JENKINS_API_TOKEN = credentials('jenkins-token') // Jenkins credential ID for Jenkins API token
    }

    stages {
        stage('Checkout') {
            steps {
                // Use script block for better error handling and future extensibility
                script {
                    git branch: 'main',
                        url: 'https://github.com/El-Vaibhav/PR_Override.git'
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip3 install requests'
            }
        }

        stage('Run Override Script') {
            steps {
                sh 'python3 "Override Insight Engine.py"'
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
