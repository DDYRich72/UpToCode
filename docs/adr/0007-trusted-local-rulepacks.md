# ADR 0007: Trusted Local Rulepacks

External Python rulepacks execute code and are therefore an explicit local trust
decision. Local mode may load configured paths or entry points; hosted mode never
does. Load failure is a configuration error, never a silent skip.
