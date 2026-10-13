"""Resolve one exact Windows session, or one unambiguous replacement on its endpoint."""
def resolve_session(key,sessions,identity=None):
    if key in sessions: return key
    if not isinstance(identity,dict) or not identity.get('identifier') or not identity.get('device'): return None
    matches=[candidate for candidate,session in sessions.items() if session.get('identifier')==identity['identifier'] and session.get('device_id')==identity['device']]
    return matches[0] if len(matches)==1 else None
