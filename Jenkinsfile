pipeline {
    agent any

    environment {
        JIRA_EMAIL = credentials('jira-email')           // Add as Jenkins credential
        JIRA_API_TOKEN = credentials('jira-token')       // Add as Jenkins credential
        JENKINS_USER = credentials('jenkins-user')       // Add as Jenkins credential
        JENKINS_API_TOKEN = credentials('jenkins-token') // Add as Jenkins credential
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                git 'https://github.com/El-Vaibhav/PR_Override.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip install requests'
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
