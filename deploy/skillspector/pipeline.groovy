pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout()
        quietPeriod(0)
        buildDiscarder(logRotator(daysToKeepStr: '30'))
    }

    environment {
        PATH = "/opt/venv/bin:/usr/local/bin:${env.PATH}"
        REPORT_DIR = "${WORKSPACE}/reports"
        LOCAL_REPO_ROOT = "${env.WITTYHUB_REPOSITORY_ROOT ?: '/opt/wittyhub/skill-repositories'}"
    }

    parameters {
        string(name: 'GIT_URL', defaultValue: 'https://github.com/JunchengDwain/SkillSpector.git',
               description: 'Git Repository URL to clone')
        string(name: 'REF', defaultValue: 'main',
               description: 'Branch / Tag / Commit SHA')
        string(name: 'SKILL_PATH', defaultValue: '',
               description: 'Relative Skill Path (leave empty for repo root)')
        string(name: 'SCANNERS', defaultValue: 'skillspector',
               description: 'Comma separated scanners')
    }

    stages {
        stage("Checkout") {
            steps {
                script {
                    deleteDir()
                    withEnv([
                        "SCAN_GIT_URL=${params.GIT_URL?.trim()}",
                        "SCAN_GIT_REF=${params.REF?.trim() ?: 'main'}",
                        "SCAN_SKILL_PATH=${params.SKILL_PATH?.trim() ?: ''}",
                    ]) {
                        sh "wittyhub-skillspector-checkout"
                    }
                }
            }
        }

        stage("Detect Skill") {
            steps {
                script {
                    if (params.SKILL_PATH?.trim()) {
                        SKILL_DIR = "${WORKSPACE}/${params.SKILL_PATH}"
                    } else {
                        SKILL_DIR = "${WORKSPACE}"
                    }
                    sh "ls -la \$(realpath '${SKILL_DIR}')/"

                    SCANNER_LIST = params.SCANNERS.split(",").collect { it.trim() }.findAll { it }
                    echo "Scan dir  : ${SKILL_DIR}"
                    echo "Scanners  : ${SCANNER_LIST}"
                }
            }
        }

        stage("Parallel Scan") {
            steps {
                script {
                    def jobs = [:]
                    SCANNER_LIST.each { scanner ->
                        jobs[scanner] = {
                            switch(scanner) {
                                case "skillspector":
                                    sh """
                                        set -ux

                                        mkdir -p "${REPORT_DIR}/${scanner}"

                                        skillspector scan \\
                                            "${SKILL_DIR}" \\
                                            --no-llm \\
                                            --format json -o "${REPORT_DIR}/${scanner}/report.json" \\
                                            --format markdown -o "${REPORT_DIR}/${scanner}/report.md" || true
                                    """
                                    break
                                default:
                                    error("Unknown scanner: ${scanner}")
                            }
                        }
                    }
                    parallel jobs
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**/*', fingerprint: true, allowEmptyArchive: true
            deleteDir()
        }
    }
}
