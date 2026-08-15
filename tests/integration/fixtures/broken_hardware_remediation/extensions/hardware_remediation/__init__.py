# -*- coding: utf-8 -*-
"""Broken hardware remediation extension fixture.

Used by integration tests to verify that ``main.py`` gracefully degrades
when an add-on extension fails to import at startup.
"""

raise ImportError("simulated broken hardware_remediation add-on")
