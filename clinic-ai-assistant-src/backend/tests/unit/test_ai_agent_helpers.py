# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
from app.services import ai_agent
from app.services.config_loader import load_profile_config


def _profile():
    return load_profile_config("milena_dental")


def test_contains_lookup_phrase_requires_word_boundaries():
    assert ai_agent._contains_lookup_phrase("dali moe ime", "ili") is False
    assert ai_agent._contains_lookup_phrase("kontakt ili email", "ili") is True


def test_contact_clarification_detects_prefixes_and_ignores_embedded_phrase_matches():
    profile = _profile()

    assert ai_agent._is_contact_clarification("dali moe ime", profile) is True
    assert ai_agent._is_contact_clarification("Vasilie", profile) is False


def test_field_level_clarification_tracks_relevant_field_tokens_only():
    assert ai_agent._is_field_level_clarification("dali moe ime", "name") is True
    assert ai_agent._is_field_level_clarification("koj broj da ostavam", "phone") is True
    assert ai_agent._is_field_level_clarification("Vasilie", "name") is False


def test_contact_ownership_style_clarification_catches_short_phone_and_email_ownership_inputs():
    assert ai_agent._is_contact_ownership_style_clarification("na broj toj", "phone") is True
    assert ai_agent._is_contact_ownership_style_clarification("na mojata poshta", "email") is True
    assert ai_agent._is_contact_ownership_style_clarification("070000000", "phone") is False


def test_goal_redirect_reply_catches_small_talk_without_grabbing_real_overview_question():
    profile = _profile()

    social_reply = ai_agent._goal_redirect_reply("shto pravish?", profile)
    vague_reply = ai_agent._goal_redirect_reply("ajde togash", profile)

    assert social_reply is not None
    assert "стоматолошко прашање" in social_reply.casefold()
    assert vague_reply is not None
    assert "болка" in vague_reply.casefold()
    assert ai_agent._goal_redirect_reply("a shto pravite vie?", profile) is None


def test_booking_scope_clarification_stays_distinct_from_field_clarification():
    assert ai_agent._is_booking_scope_clarification("sto zakazuvame?", "phone") is True
    assert ai_agent._is_booking_scope_clarification("koja email adresa?", "email") is False


def test_classify_booking_input_prefers_clarification_for_questions():
    profile = _profile()

    assert ai_agent._classify_booking_input("dali moe ime?", profile) == ai_agent.BOOKING_INPUT_CLARIFICATION
    assert ai_agent._classify_booking_input("Marjan", profile) == ai_agent.BOOKING_INPUT_FIELD_VALUE
    assert ai_agent._classify_booking_input("   ", profile) == ai_agent.BOOKING_INPUT_FEEDBACK


def test_extract_contact_fields_from_message_strips_labels_and_normalizes_phone():
    extracted = ai_agent._extract_contact_fields_from_message(
        "ime Marjan telefon 070-000-000 email mail@test.mk",
        ["name", "phone", "email"],
        _profile(),
    )

    assert extracted == {
        "name": "Marjan",
        "phone": "070000000",
        "email": "mail@test.mk",
    }


def test_should_attempt_contact_bundle_parse_requires_explicit_bundle_signal():
    profile = _profile()

    assert ai_agent._should_attempt_contact_bundle_parse(
        "Marjan 070000000",
        ["name", "phone", "email"],
        profile,
    ) is False
    assert ai_agent._should_attempt_contact_bundle_parse(
        "ime Marjan telefon 070000000 email mail@test.mk",
        ["name", "phone", "email"],
        profile,
    ) is True


def test_persisted_fields_match_requires_successful_nonblank_required_fields():
    assert ai_agent._persisted_fields_match(
        {
            "success": True,
            "persisted_data": {"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
        },
        ["name", "phone", "email"],
    ) is True
    assert ai_agent._persisted_fields_match(
        {
            "success": True,
            "persisted_data": {"name": "Marjan", "phone": " ", "email": "mail@test.mk"},
        },
        ["name", "phone", "email"],
    ) is False


def test_recover_from_persistence_failure_retries_first_missing_field_and_clears_stale_value():
    state = {
        "stage": "completed",
        "next_field": None,
        "data": {"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    }

    retry_field = ai_agent._recover_from_persistence_failure(
        state,
        ["name", "phone", "email"],
        {"persisted_data": {"name": "Marjan", "phone": "070000000", "email": None}},
        "email",
    )

    assert retry_field == "email"
    assert state["stage"] == "collecting_contact"
    assert state["next_field"] == "email"
    assert "email" not in state["data"]


def test_invalid_phone_reply_uses_human_singular_and_plural_wording():
    profile = _profile()

    singular = ai_agent._invalid_phone_reply(profile, "07000000")
    plural = ai_agent._invalid_phone_reply(profile, "0700000")

    assert "ми делува дека недостига уште 1 цифра" in singular.casefold()
    assert "пратете ми го бројот уште еднаш" in singular.casefold()
    assert "ми делува дека недостигаат уште 2 цифри" in plural.casefold()
