# -*- coding: utf-8 -*-
"""
Playwright Browser Helper Module
Provides helper functions for browser automation using system Edge browser
"""

import logging
from typing import Any, Dict, Literal, Optional  # noqa: F401

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

logger = logging.getLogger(__name__)


class PlaywrightHelper:
    """Helper class for Playwright browser automation"""

    def __init__(self, headless: bool = True):
        """
        Initialize Playwright helper

        Args:
            headless: Run browser in headless mode (default: True)
        """
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self) -> bool:
        """
        Start browser session

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.playwright = sync_playwright().start()

            # Use system Edge browser for stability
            self.browser = self.playwright.chromium.launch(
                channel="msedge",
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            # Create browser context
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            )
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )

            # Create page
            self.page = self.context.new_page()

            logger.info("Browser session started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start browser session: {e}")  # noqa: F541
            self.cleanup()
            return False

    def navigate(
        self,
        url: str,  # noqa: E501
        wait_until: Literal["load", "domcontentloaded", "networkidle"] = "networkidle",
    ) -> bool:
        """
        Navigate to URL

        Args:
            url: Target URL
            wait_until: Navigation wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            bool: True if successful, False otherwise
        """
        """
        Navigate to URL

        Args:
            url: Target URL
            wait_until: Navigation wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.page:
            logger.error("Browser not started")
            return False

        try:
            self.page.goto(url, wait_until=wait_until)
            logger.info(f"Navigated to {url}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")  # noqa: F541
            return False

    def get_page_title(self) -> Optional[str]:
        """
        Get current page title

        Returns:
            Page title or None if failed
        """
        if not self.page:
            logger.error("Browser not started")
            return None

        try:
            title = self.page.title()
            logger.info(f"Page title: {title}")  # noqa: F541
            return title

        except Exception as e:
            logger.error(f"Failed to get page title: {e}")  # noqa: F541
            return None

    def get_page_content(self) -> Optional[str]:
        """
        Get current page content

        Returns:
            Page content or None if failed
        """
        if not self.page:
            logger.error("Browser not started")
            return None

        try:
            content = self.page.content()
            logger.info(f"Retrieved page content, length: {len(content)}")  # noqa: F541
            return content

        except Exception as e:
            logger.error(f"Failed to get page content: {e}")  # noqa: F541
            return None

    def take_screenshot(self, path: str) -> bool:
        """
        Take screenshot of current page

        Args:
            path: Screenshot file path

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.page:
            logger.error("Browser not started")
            return False

        try:
            self.page.screenshot(path=path)
            logger.info(f"Screenshot saved to {path}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")  # noqa: F541
            return False

    def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript in page context

        Args:
            script: JavaScript code to execute

        Returns:
            Script result or None if failed
        """
        if not self.page:
            logger.error("Browser not started")
            return None

        try:
            result = self.page.evaluate(script)
            logger.info(f"Script executed successfully")  # noqa: F541
            return result

        except Exception as e:
            logger.error(f"Failed to execute script: {e}")  # noqa: F541
            return None

    def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """
        Wait for element to appear

        Args:
            selector: CSS selector
            timeout: Maximum wait time in milliseconds

        Returns:
            bool: True if element found, False otherwise
        """
        if not self.page:
            logger.error("Browser not started")
            return False

        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"Element found: {selector}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Element not found: {selector}, error: {e}")  # noqa: F541
            return False

    def click(self, selector: str) -> bool:
        """
        Click element

        Args:
            selector: CSS selector

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.page:
            logger.error("Browser not started")
            return False

        try:
            self.page.click(selector)
            logger.info(f"Clicked element: {selector}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to click element: {selector}, error: {e}")  # noqa: F541
            return False

    def fill(self, selector: str, value: str) -> bool:
        """
        Fill input field

        Args:
            selector: CSS selector
            value: Value to fill

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.page:
            logger.error("Browser not started")
            return False

        try:
            self.page.fill(selector, value)
            logger.info(f"Filled element: {selector} with value: {value}")  # noqa: F541
            return True

        except Exception as e:
            logger.error(f"Failed to fill element: {selector}, error: {e}")  # noqa: F541
            return False

    def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")  # noqa: F541

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


def quick_test():
    """Quick test function to verify Playwright setup"""
    print("Running quick Playwright test...")

    with PlaywrightHelper(headless=True) as helper:
        if helper.navigate("https://example.com"):
            title = helper.get_page_title()
            if title:
                print(f"Test successful! Page title: {title}")  # noqa: F541
                return True

    print("Test failed")
    return False


if __name__ == "__main__":
    quick_test()
