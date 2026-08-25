# -*- coding: utf-8 -*-
"""
Notification Advanced API Router
Provides comprehensive CRUD operations for notification management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from loguru import logger

router = APIRouter(prefix="/api/v1/notify", tags=["Notification Advanced"])


# Pydantic Models
class ChannelCreate(BaseModel):
    """Notification channel creation model"""
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type (email, slack, pagerduty, sms, webhook, teams)")
    enabled: bool = Field(default=True, description="Whether the channel is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Channel configuration")
    priority: int = Field(default=0, description="Channel priority")
    retry_count: int = Field(default=3, description="Number of retries on failure")
    timeout: int = Field(default=30, description="Timeout in seconds")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = ["email", "slack", "pagerduty", "sms", "webhook", "teams"]
        if v not in valid_types:
            raise ValueError(f"Invalid channel type. Must be one of: {', '.join(valid_types)}")
        return v


class ChannelUpdate(BaseModel):
    """Notification channel update model"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    retry_count: Optional[int] = None
    timeout: Optional[int] = None


class ChannelResponse(BaseModel):
    """Notification channel response model"""
    id: str
    name: str
    type: str
    enabled: bool
    config: Dict[str, Any]
    priority: int
    retry_count: int
    timeout: int
    created_at: datetime
    updated_at: datetime


class TemplateCreate(BaseModel):
    """Notification template creation model"""
    name: str = Field(..., description="Template name")
    subject: str = Field(..., description="Template subject")
    body: str = Field(..., description="Template body")
    type: str = Field(default="email", description="Template type")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    enabled: bool = Field(default=True, description="Whether the template is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    """Notification template update model"""
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    variables: Optional[List[str]] = None
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    """Notification template response model"""
    id: str
    name: str
    subject: str
    body: str
    type: str
    variables: List[str]
    enabled: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RuleCreate(BaseModel):
    """Notification rule creation model"""
    name: str = Field(..., description="Rule name")
    condition: str = Field(..., description="Rule condition expression")
    channels: List[str] = Field(..., description="Channel IDs to notify")
    template_id: str = Field(..., description="Template ID to use")
    enabled: bool = Field(default=True, description="Whether the rule is enabled")
    priority: int = Field(default=0, description="Rule priority")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuleUpdate(BaseModel):
    """Notification rule update model"""
    name: Optional[str] = None
    condition: Optional[str] = None
    channels: Optional[List[str]] = None
    template_id: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class RuleResponse(BaseModel):
    """Notification rule response model"""
    id: str
    name: str
    condition: str
    channels: List[str]
    template_id: str
    enabled: bool
    priority: int
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NotificationHistoryResponse(BaseModel):
    """Notification history response model"""
    id: str
    channel_id: str
    channel_name: str
    rule_id: Optional[str]
    template_id: str
    status: str
    error_message: Optional[str]
    sent_at: datetime
    metadata: Dict[str, Any]


class NotificationSettings(BaseModel):
    """Notification settings model"""
    enabled: bool = Field(default=True, description="Global notification enabled")
    min_level: str = Field(default="info", description="Minimum notification level")
    rate_limit_enabled: bool = Field(default=True, description="Rate limiting enabled")
    rate_limit_per_minute: int = Field(default=10, description="Max notifications per minute")
    batch_enabled: bool = Field(default=False, description="Batch notifications enabled")
    batch_interval: int = Field(default=60, description="Batch interval in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# In-memory storage (in production, use a database)
_channels: Dict[str, Dict[str, Any]] = {}
_templates: Dict[str, Dict[str, Any]] = {}
_rules: Dict[str, Dict[str, Any]] = {}
_history: List[Dict[str, Any]] = []
_settings: Dict[str, Any] = {
    "enabled": True,
    "min_level": "info",
    "rate_limit_enabled": True,
    "rate_limit_per_minute": 10,
    "batch_enabled": False,
    "batch_interval": 60,
    "metadata": {},
}


def _initialize_default_data():
    """Initialize default data"""
    # Default channels
    if not _channels:
        default_channels = [
            {
                "id": str(uuid4()),
                "name": "Email Channel",
                "type": "email",
                "enabled": True,
                "config": {
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "from_address": "alerts@example.com",
                },
                "priority": 10,
                "retry_count": 3,
                "timeout": 30,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "id": str(uuid4()),
                "name": "Slack Channel",
                "type": "slack",
                "enabled": True,
                "config": {
                    "webhook_url": "https://hooks.slack.com/services/xxx",
                    "channel": "#alerts",
                },
                "priority": 5,
                "retry_count": 3,
                "timeout": 30,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
        for channel in default_channels:
            _channels[channel["id"]] = channel

    # Default templates
    if not _templates:
        default_templates = [
            {
                "id": str(uuid4()),
                "name": "Alert Template",
                "subject": "Alert: {{alert_title}}",
                "body": "Alert Details:\n\nTitle: {{alert_title}}\nLevel: {{alert_level}}\nDescription: {{alert_description}}\nTime: {{alert_time}}",
                "type": "email",
                "variables": ["alert_title", "alert_level", "alert_description", "alert_time"],
                "enabled": True,
                "metadata": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
        for template in default_templates:
            _templates[template["id"]] = template

    # Default rules
    if not _rules:
        template_id = list(_templates.keys())[0] if _templates else str(uuid4())
        channel_id = list(_channels.keys())[0] if _channels else str(uuid4())
        
        default_rules = [
            {
                "id": str(uuid4()),
                "name": "Critical Alert Rule",
                "condition": "alert_level == 'critical'",
                "channels": [channel_id],
                "template_id": template_id,
                "enabled": True,
                "priority": 10,
                "metadata": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
        for rule in default_rules:
            _rules[rule["id"]] = rule


_initialize_default_data()


# Channel Endpoints
@router.get("/channels", response_model=List[ChannelResponse], summary="Get all notification channels")
async def get_channels(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    type: Optional[str] = Query(None, description="Filter by channel type")
):
    """
    Get all notification channels with optional filtering
    
    Args:
        enabled: Filter by enabled status
        type: Filter by channel type
        
    Returns:
        List of notification channels
    """
    try:
        channels = list(_channels.values())
        
        if enabled is not None:
            channels = [ch for ch in channels if ch["enabled"] == enabled]
        
        if type:
            channels = [ch for ch in channels if ch["type"] == type]
        
        # Sort by priority
        channels.sort(key=lambda x: x["priority"], reverse=True)
        
        return [ChannelResponse(**ch) for ch in channels]
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels", response_model=ChannelResponse, summary="Create a new notification channel")
async def create_channel(channel: ChannelCreate):
    """
    Create a new notification channel
    
    Args:
        channel: Channel data
        
    Returns:
        Created channel
    """
    try:
        new_channel = {
            "id": str(uuid4()),
            "name": channel.name,
            "type": channel.type,
            "enabled": channel.enabled,
            "config": channel.config,
            "priority": channel.priority,
            "retry_count": channel.retry_count,
            "timeout": channel.timeout,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        _channels[new_channel["id"]] = new_channel
        
        logger.info(f"Created notification channel: {channel.name}")
        return ChannelResponse(**new_channel)
    except Exception as e:
        logger.error(f"Error creating channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}", response_model=ChannelResponse, summary="Get a channel by ID")
async def get_channel(channel_id: str):
    """
    Get a notification channel by ID
    
    Args:
        channel_id: Channel ID
        
    Returns:
        Channel data
    """
    try:
        if channel_id not in _channels:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return ChannelResponse(**_channels[channel_id])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/channels/{channel_id}", response_model=ChannelResponse, summary="Update a channel")
async def update_channel(channel_id: str, channel: ChannelUpdate):
    """
    Update a notification channel
    
    Args:
        channel_id: Channel ID
        channel: Updated channel data
        
    Returns:
        Updated channel
    """
    try:
        if channel_id not in _channels:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        existing = _channels[channel_id]
        
        if channel.name is not None:
            existing["name"] = channel.name
        if channel.enabled is not None:
            existing["enabled"] = channel.enabled
        if channel.config is not None:
            existing["config"] = channel.config
        if channel.priority is not None:
            existing["priority"] = channel.priority
        if channel.retry_count is not None:
            existing["retry_count"] = channel.retry_count
        if channel.timeout is not None:
            existing["timeout"] = channel.timeout
        
        existing["updated_at"] = datetime.utcnow()
        
        logger.info(f"Updated notification channel: {channel_id}")
        return ChannelResponse(**existing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/channels/{channel_id}", summary="Delete a channel")
async def delete_channel(channel_id: str):
    """
    Delete a notification channel
    
    Args:
        channel_id: Channel ID
        
    Returns:
        Deletion result
    """
    try:
        if channel_id not in _channels:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Check if channel is used by any rules
        for rule in _rules.values():
            if channel_id in rule["channels"]:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete channel: it is used by one or more notification rules"
                )
        
        del _channels[channel_id]
        
        logger.info(f"Deleted notification channel: {channel_id}")
        return {"status": "success", "message": "Channel deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Template Endpoints
@router.get("/templates", response_model=List[TemplateResponse], summary="Get all notification templates")
async def get_templates(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    type: Optional[str] = Query(None, description="Filter by template type")
):
    """
    Get all notification templates with optional filtering
    
    Args:
        enabled: Filter by enabled status
        type: Filter by template type
        
    Returns:
        List of notification templates
    """
    try:
        templates = list(_templates.values())
        
        if enabled is not None:
            templates = [t for t in templates if t["enabled"] == enabled]
        
        if type:
            templates = [t for t in templates if t["type"] == type]
        
        return [TemplateResponse(**t) for t in templates]
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates", response_model=TemplateResponse, summary="Create a new notification template")
async def create_template(template: TemplateCreate):
    """
    Create a new notification template
    
    Args:
        template: Template data
        
    Returns:
        Created template
    """
    try:
        new_template = {
            "id": str(uuid4()),
            "name": template.name,
            "subject": template.subject,
            "body": template.body,
            "type": template.type,
            "variables": template.variables,
            "enabled": template.enabled,
            "metadata": template.metadata,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        _templates[new_template["id"]] = new_template
        
        logger.info(f"Created notification template: {template.name}")
        return TemplateResponse(**new_template)
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=TemplateResponse, summary="Get a template by ID")
async def get_template(template_id: str):
    """
    Get a notification template by ID
    
    Args:
        template_id: Template ID
        
    Returns:
        Template data
    """
    try:
        if template_id not in _templates:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return TemplateResponse(**_templates[template_id])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/templates/{template_id}", response_model=TemplateResponse, summary="Update a template")
async def update_template(template_id: str, template: TemplateUpdate):
    """
    Update a notification template
    
    Args:
        template_id: Template ID
        template: Updated template data
        
    Returns:
        Updated template
    """
    try:
        if template_id not in _templates:
            raise HTTPException(status_code=404, detail="Template not found")
        
        existing = _templates[template_id]
        
        if template.name is not None:
            existing["name"] = template.name
        if template.subject is not None:
            existing["subject"] = template.subject
        if template.body is not None:
            existing["body"] = template.body
        if template.type is not None:
            existing["type"] = template.type
        if template.variables is not None:
            existing["variables"] = template.variables
        if template.enabled is not None:
            existing["enabled"] = template.enabled
        if template.metadata is not None:
            existing["metadata"] = template.metadata
        
        existing["updated_at"] = datetime.utcnow()
        
        logger.info(f"Updated notification template: {template_id}")
        return TemplateResponse(**existing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}", summary="Delete a template")
async def delete_template(template_id: str):
    """
    Delete a notification template
    
    Args:
        template_id: Template ID
        
    Returns:
        Deletion result
    """
    try:
        if template_id not in _templates:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if template is used by any rules
        for rule in _rules.values():
            if rule["template_id"] == template_id:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete template: it is used by one or more notification rules"
                )
        
        del _templates[template_id]
        
        logger.info(f"Deleted notification template: {template_id}")
        return {"status": "success", "message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Rule Endpoints
@router.get("/rules", response_model=List[RuleResponse], summary="Get all notification rules")
async def get_rules(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status")
):
    """
    Get all notification rules with optional filtering
    
    Args:
        enabled: Filter by enabled status
        
    Returns:
        List of notification rules
    """
    try:
        rules = list(_rules.values())
        
        if enabled is not None:
            rules = [r for r in rules if r["enabled"] == enabled]
        
        # Sort by priority
        rules.sort(key=lambda x: x["priority"], reverse=True)
        
        return [RuleResponse(**r) for r in rules]
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", response_model=RuleResponse, summary="Create a new notification rule")
async def create_rule(rule: RuleCreate):
    """
    Create a new notification rule
    
    Args:
        rule: Rule data
        
    Returns:
        Created rule
    """
    try:
        # Validate template exists
        if rule.template_id not in _templates:
            raise HTTPException(status_code=400, detail="Template not found")
        
        # Validate channels exist
        for channel_id in rule.channels:
            if channel_id not in _channels:
                raise HTTPException(status_code=400, detail=f"Channel {channel_id} not found")
        
        new_rule = {
            "id": str(uuid4()),
            "name": rule.name,
            "condition": rule.condition,
            "channels": rule.channels,
            "template_id": rule.template_id,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "metadata": rule.metadata,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        _rules[new_rule["id"]] = new_rule
        
        logger.info(f"Created notification rule: {rule.name}")
        return RuleResponse(**new_rule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=RuleResponse, summary="Get a rule by ID")
async def get_rule(rule_id: str):
    """
    Get a notification rule by ID
    
    Args:
        rule_id: Rule ID
        
    Returns:
        Rule data
    """
    try:
        if rule_id not in _rules:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return RuleResponse(**_rules[rule_id])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/rules/{rule_id}", response_model=RuleResponse, summary="Update a rule")
async def update_rule(rule_id: str, rule: RuleUpdate):
    """
    Update a notification rule
    
    Args:
        rule_id: Rule ID
        rule: Updated rule data
        
    Returns:
        Updated rule
    """
    try:
        if rule_id not in _rules:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        existing = _rules[rule_id]
        
        if rule.name is not None:
            existing["name"] = rule.name
        if rule.condition is not None:
            existing["condition"] = rule.condition
        if rule.channels is not None:
            # Validate channels exist
            for channel_id in rule.channels:
                if channel_id not in _channels:
                    raise HTTPException(status_code=400, detail=f"Channel {channel_id} not found")
            existing["channels"] = rule.channels
        if rule.template_id is not None:
            if rule.template_id not in _templates:
                raise HTTPException(status_code=400, detail="Template not found")
            existing["template_id"] = rule.template_id
        if rule.enabled is not None:
            existing["enabled"] = rule.enabled
        if rule.priority is not None:
            existing["priority"] = rule.priority
        if rule.metadata is not None:
            existing["metadata"] = rule.metadata
        
        existing["updated_at"] = datetime.utcnow()
        
        logger.info(f"Updated notification rule: {rule_id}")
        return RuleResponse(**existing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}", summary="Delete a rule")
async def delete_rule(rule_id: str):
    """
    Delete a notification rule
    
    Args:
        rule_id: Rule ID
        
    Returns:
        Deletion result
    """
    try:
        if rule_id not in _rules:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        del _rules[rule_id]
        
        logger.info(f"Deleted notification rule: {rule_id}")
        return {"status": "success", "message": "Rule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# History Endpoints
@router.get("/history", response_model=List[NotificationHistoryResponse], summary="Get notification history")
async def get_notification_history(
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records")
):
    """
    Get notification history with optional filtering
    
    Args:
        channel_id: Filter by channel ID
        status: Filter by status
        limit: Maximum number of records
        
    Returns:
        List of notification history records
    """
    try:
        history = _history.copy()
        
        if channel_id:
            history = [h for h in history if h["channel_id"] == channel_id]
        
        if status:
            history = [h for h in history if h["status"] == status]
        
        # Sort by sent time (newest first)
        history.sort(key=lambda x: x["sent_at"], reverse=True)
        
        # Limit results
        history = history[:limit]
        
        return [NotificationHistoryResponse(**h) for h in history]
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Settings Endpoints
@router.get("/settings", response_model=NotificationSettings, summary="Get notification settings")
async def get_notification_settings():
    """
    Get global notification settings
    
    Returns:
        Notification settings
    """
    try:
        return NotificationSettings(**_settings)
    except Exception as e:
        logger.error(f"Error getting notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/settings", response_model=NotificationSettings, summary="Update notification settings")
async def update_notification_settings(settings: NotificationSettings):
    """
    Update global notification settings
    
    Args:
        settings: Updated settings
        
    Returns:
        Updated settings
    """
    try:
        _settings.update(settings.model_dump(exclude_unset=True))
        
        logger.info("Updated notification settings")
        return NotificationSettings(**_settings)
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
