function normalizeError(event) {
  const execution = event.execution || {}, trigger = event.trigger || {};
  const error = execution.error || trigger.error || {};
  return {
    workflow: event.workflow?.name || 'Unknown workflow',
    step: execution.lastNodeExecuted || error.node?.name || trigger.mode || 'Trigger / unavailable',
    message: error.message || error.cause?.message || 'No error message supplied',
    url: execution.url || 'No execution URL supplied'
  };
}
if (typeof module !== 'undefined') module.exports = {normalizeError};
