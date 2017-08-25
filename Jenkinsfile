#!/usr/bin/env groovy

// Note:
// Activating the virtualenv doesn't stay active across
// sh invocations in pipeline scripts.
// See https://issues.jenkins-ci.org/browse/JENKINS-37116

pipeline {
    agent any
    stages {

        stage('Prepare build') {
            steps {
                slackNotify("STARTED")
                checkout scm
                sh "spynl/cli/ops/prepare-stage.sh -u $scm_urls -r $revision -f $fallbackrevision -m"
            }
            post {
                always {
                    archive 'repo-state.txt'
                }
            }
        }

        stage('Unit Tests') {
            steps {
                sh "source venv/bin/activate && pip install pytest-cov && spynl dev.test --reports"
            }
            post {
                always {
                    junit 'venv/**/pytests.xml'
                    //coverage 'venv/**/coverage.xml'  // Check this ticket: https://issues.jenkins-ci.org/browse/JENKINS-30700
                }
            }
        }

        stage('Deploy') {
            steps {
                sh "spynl/cli/ops/prepare-stage.sh -u $scm_urls -r $revision -f $fallbackrevision"
                sh "source venv/bin/activate && spynl ops.deploy --buildnr ${env.BUILD_NUMBER} --task $task"
            }
            post {
                always {
                    archive 'spynl/cli/ops/docker/docker.build.log'
                }
            }
        }

        stage('Smoke Tests') {
            when {
                not {environment name: 'task', value: 'production'}
            }
            steps {
                sleep time:90, unit:'SECONDS'
                sh "source venv/bin/activate && spynl ops.smoke_test --task $task"
            }
            post {
                failure {  // Rollback to latest successful spynl image
                    script {
                        try {
                            sh "source venv/bin/activate && spynl ops.deploy --task $task --rollback"
                        } catch(rollback_error) {
                            slackNotify("Rollback failed, <$task> is down")
                            throw rollback_error
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            slackNotify(currentBuild.result)
        }
    }
}


// Send Slack Notifications
def slackNotify(String buildStatus = 'STARTED') {
  buildStatus =  buildStatus ?: 'SUCCESSFUL'

  def colorCode = '#e60000'

  if (buildStatus == 'STARTED') {
    colorCode = '#ff8c00'
  } else if (buildStatus == 'SUCCESSFUL') {
    colorCode = '#32cd32'
  } else {
    colorCode = '#e60000'
  }

  slackSend (color: "${colorCode}", message: "${buildStatus}: Job ${env.JOB_NAME.replaceAll('%2F', '/')} Build ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)")
}
