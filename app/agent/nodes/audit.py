from app.mcp.server import log_reasoning


async def audit_agent_action(
    user_id: str,
    agent_name: str,
    action: str,
    payload: dict
):
    return await log_reasoning(
        user_id=user_id,
        agent_name=agent_name,
        action=action,
        payload=payload
    )
