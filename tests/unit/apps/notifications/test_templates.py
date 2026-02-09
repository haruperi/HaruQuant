import pytest
from apps.notifications.templates import NotificationTemplate, NotificationError


class TestNotificationTemplate:
    @pytest.fixture
    def template(self):
        return NotificationTemplate()

    def test_defaults(self, template):
        assert "trading_alert" in template.templates
        assert "system_alert" in template.templates
        assert "error_alert" in template.templates

    def test_render_success(self, template):
        msg = template.render(
            "trading_alert",
            symbol="EURUSD",
            action="BUY",
            price="1.1000",
            reason="Signal",
            account="Demo",
            strategy="MACD",
            risk_level="Low"
        )
        assert "EURUSD" in msg.title
        assert "BUY" in msg.title
        assert "1.1000" in msg.body

    def test_render_missing_args(self, template):
        with pytest.raises(NotificationError):
            template.render("trading_alert", symbol="EURUSD")

    def test_render_unknown_template(self, template):
        with pytest.raises(NotificationError):
            template.render("unknown")

    def test_add_update_remove(self, template):
        # Add
        template.add_template("new", "{var}", "{var}")
        assert "new" in template.templates
        
        # Update
        template.update_template("new", title_template="New {var}")
        assert template.templates["new"]["title"] == "New {var}"
        
        # Remove
        template.remove_template("new")
        assert "new" not in template.templates

    def test_remove_essential_error(self, template):
        with pytest.raises(NotificationError):
            template.remove_template("trading_alert")

    def test_get_variables(self, template):
        vars = template.get_template_variables("trading_alert")
        assert "symbol" in vars
        assert "action" in vars
        # timestamp is auto-added if missing, but checking template vars
        # Actually timestamp IS in the template text, so it should be returned
        assert "timestamp" in vars

    def test_validate(self, template):
        missing = template.validate_template("trading_alert", symbol="EURUSD")
        assert "action" in missing
        assert len(missing) > 0
        
        missing = template.validate_template("custom_message", title="T", body="B")
        assert len(missing) == 0

    def test_preview(self, template):
        preview = template.preview_template("custom_message", title="T", body="B")
        assert "Title: T" in preview
        assert "Body:\nB" in preview

    def test_import_export(self, template):
        exported = template.export_templates()
        assert "trading_alert" in exported
        
        new_template = NotificationTemplate()
        # clear defaults to test import
        new_template.templates = {}
        new_template.import_templates(exported)
        
        assert "trading_alert" in new_template.templates
        
    def test_get_info(self, template):
        info = template.get_template_info("trading_alert")
        assert info["name"] == "trading_alert"
        assert len(info["required_variables"]) > 0
