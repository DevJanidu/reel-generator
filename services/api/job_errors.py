"""Public diagnoses are fixed text; detailed errors remain private and bounded."""
MESSAGES={
 'AUTHENTICATION':'Provider authentication is required. Refresh the official CLI login or authorized credential, then retry.',
 'USAGE_LIMIT':'The provider reported a usage limit. Check the provider account before retrying.',
 'RATE_LIMIT':'The provider rate-limited this request. Wait before explicitly retrying.',
 'TIMEOUT':'The configured worker deadline expired before a complete response was available. Review the last provider activity and timeout setting before retrying.',
 'NOT_INSTALLED':'The configured CLI executable was not found. Check the provider installation.',
 'NETWORK':'The provider connection failed. Check connectivity before retrying.',
 'PROCESS_SPAWN':'The provider process could not be started. Check its installation and permissions.',
 'PROCESS_EXIT':'The provider process exited unsuccessfully. Review private diagnostics before retrying.',
 'INVALID_OUTPUT':'The provider response was empty, incomplete or invalid JSON/schema. No successful package is claimed.',
 'ARTIFACT_PERSISTENCE':'The validated output could not be saved. Review storage permissions and retry explicitly.',
 'ISOLATION_UNAVAILABLE':'Native isolation verification failed. Automatic execution remains disabled.',
 'CANCELLED':'The owner cancelled this attempt.',
 'PROVIDER_FAILED':'The provider attempt failed for an unclassified reason. Review its private diagnostics before retrying.',
 'PROVIDER_UNAVAILABLE':'The provider reported that its service is unavailable. Wait and retry explicitly.',
}
def category(error):
 from .providers import classify
 text=str(error).lower()
 for token,code in [('artifact_persistence','ARTIFACT_PERSISTENCE'),('rate limit','RATE_LIMIT'),('rate_limit','RATE_LIMIT'),('not_installed','NOT_INSTALLED'),('process_spawn','PROCESS_SPAWN'),('filenotfounderror','PROCESS_SPAWN'),('process_exit','PROCESS_EXIT'),('exited unsuccessfully','PROCESS_EXIT'),('network','NETWORK'),('connection reset','NETWORK'),('invalid_output','INVALID_OUTPUT')]:
  if token in text:return code
 return classify(str(error))
def diagnosis(error):
 code=category(error);return dict(category=code,message=MESSAGES.get(code,MESSAGES['PROVIDER_FAILED']))
