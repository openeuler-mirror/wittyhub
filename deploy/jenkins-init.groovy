import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import hudson.model.ParametersDefinitionProperty
import hudson.model.StringParameterDefinition

def instance = Jenkins.get()

// 0. 跳过 setup wizard
instance.installState = InstallState.INITIAL_SETUP_COMPLETED
println "[init] Setup wizard disabled"

// 1. 创建/重置 admin 用户
def hudsonRealm = new HudsonPrivateSecurityRealm(false)
def adminUser = hudsonRealm.getUser("admin")
if (adminUser == null) {
    hudsonRealm.createAccount("admin", "ADMIN_PASS_PLACEHOLDER")
    println "[init] admin user created"
} else {
    hudsonRealm.createAccount("admin", "ADMIN_PASS_PLACEHOLDER")
    println "[init] admin password reset"
}
instance.setSecurityRealm(hudsonRealm)

// 2. 设置授权策略
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)
instance.save()

// 3. 创建 skill-scanner Pipeline Job
def jobName = "skill-scanner"
def job = instance.getItem(jobName)

if (job == null) {
    try {
        job = instance.createProjectFromXML(jobName, new java.io.ByteArrayInputStream(
            '<?xml version="1.1" encoding="UTF-8"?><flow-definition plugin="workflow-job@2.42"/></flow-definition>'.bytes
        ))
        println "[init] ${jobName} job created"
    } catch (Exception e) {
        println "[init] createProjectFromXML failed: ${e.message}"
        // 回退方案: 手动创建 job 目录和 config.xml，然后 reload
        def jobsDir = new File(instance.getRootDir(), "jobs/${jobName}")
        jobsDir.mkdirs()
        def configFile = new File(jobsDir, "config.xml")
        configFile.text = '<?xml version="1.1" encoding="UTF-8"?><flow-definition plugin="workflow-job@2.42"><actions/><description></description><keepDependencies>false</keepDependencies><properties><hudson.model.ParametersDefinitionProperty><parameterDefinitions><hudson.model.StringParameterDefinition><name>GIT_URL</name><description>Git Repository URL to clone</description><defaultValue>https://github.com/JunchengDwain/SkillSpector.git</defaultValue><trim>false</trim></hudson.model.StringParameterDefinition><hudson.model.StringParameterDefinition><name>REF</name><description>Branch / Tag / Commit SHA</description><defaultValue>main</defaultValue><trim>false</trim></hudson.model.StringParameterDefinition><hudson.model.StringParameterDefinition><name>SKILL_PATH</name><description>Relative Skill Path</description><defaultValue></defaultValue><trim>false</trim></hudson.model.StringParameterDefinition><hudson.model.StringParameterDefinition><name>SCANNERS</name><description>Comma separated scanners</description><defaultValue>skillspector</defaultValue><trim>false</trim></hudson.model.StringParameterDefinition></parameterDefinitions></hudson.model.ParametersDefinitionProperty></properties><definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps@2.94"><script/><sandbox>true</sandbox></definition><triggers/><disabled>false</disabled></flow-definition>'
        instance.reload()
        println "[init] ${jobName} job created via fallback, reloaded"
        job = instance.getItem(jobName)
    }
} else {
    println "[init] ${jobName} job already exists, updating definition"
}

// 读取 Pipeline 脚本
def pipelineFile = new File("/usr/share/jenkins/ref/jenkins-pipeline.groovy")
def pipelineScript = pipelineFile.text
job.definition = new CpsFlowDefinition(pipelineScript, true)

// 添加参数
def params = new ParametersDefinitionProperty([
    new StringParameterDefinition("GIT_URL", "https://github.com/JunchengDwain/SkillSpector.git", "Git Repository URL to clone"),
    new StringParameterDefinition("REF", "main", "Branch / Tag / Commit SHA"),
    new StringParameterDefinition("SKILL_PATH", "", "Relative Skill Path"),
    new StringParameterDefinition("SCANNERS", "skillspector", "Comma separated scanners")
])
job.addProperty(params)
job.save()
instance.save()

println "[init] Initialization complete: admin user and skill-scanner job ready"