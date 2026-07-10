from fastshot.platforms.macos import (
    _ax_ancestry_has_any_role,
    _intersect_rects,
    _tuple_rect_contains,
)


def test_intersect_rects_clips_accessibility_bounds_to_window() -> None:
    assert _intersect_rects((10, 0, 678, 650), (10, 25, 678, 625)) == (
        10,
        25,
        678,
        625,
    )


def test_intersect_rects_rejects_disjoint_bounds() -> None:
    assert _intersect_rects((0, 0, 10, 10), (20, 20, 10, 10)) is None


def test_link_role_is_detected_on_accessibility_parent() -> None:
    class Accessibility:
        kAXErrorSuccess = 0
        kAXRoleAttribute = "role"
        kAXParentAttribute = "parent"

        @staticmethod
        def AXUIElementCopyAttributeValue(element, attribute, _placeholder):
            value = element.get(attribute)
            return (0, value) if value is not None else (1, None)

    link = {"role": "AXLink"}
    text = {"role": "AXStaticText", "parent": link}
    assert _ax_ancestry_has_any_role(text, {"AXLink", "AXWebArea"}, Accessibility)


def test_web_area_role_is_detected_above_nested_page_content() -> None:
    class Accessibility:
        kAXErrorSuccess = 0
        kAXRoleAttribute = "role"
        kAXParentAttribute = "parent"

        @staticmethod
        def AXUIElementCopyAttributeValue(element, attribute, _placeholder):
            value = element.get(attribute)
            return (0, value) if value is not None else (1, None)

    web_area = {"role": "AXWebArea"}
    group = {"role": "AXGroup", "parent": web_area}
    text = {"role": "AXStaticText", "parent": group}
    assert _ax_ancestry_has_any_role(text, {"AXWebArea"}, Accessibility)


def test_hit_test_target_must_contain_cursor() -> None:
    status_url = (0, 1030, 620, 20)
    assert not _tuple_rect_contains(status_url, 245, 290)
    assert _tuple_rect_contains(status_url, 245, 1035)


def test_public_ax_role_strings_work_without_exported_constants() -> None:
    class Accessibility:
        kAXErrorSuccess = 0
        kAXRoleAttribute = "role"
        kAXParentAttribute = "parent"

        @staticmethod
        def AXUIElementCopyAttributeValue(element, attribute, _placeholder):
            value = element.get(attribute)
            return (0, value) if value is not None else (1, None)

    assert not hasattr(Accessibility, "kAXLinkRole")
    assert _ax_ancestry_has_any_role(
        {"role": "AXLink"},
        {getattr(Accessibility, "kAXLinkRole", "AXLink")},
        Accessibility,
    )
