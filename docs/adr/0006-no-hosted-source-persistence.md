# ADR 0006: No Hosted Source Persistence

Hosted source exists only in request memory and bounded temporary processing.
There is no upload store, report history, judgment cache, payload log, or source
telemetry. Temporary resources are destroyed before the response completes.
