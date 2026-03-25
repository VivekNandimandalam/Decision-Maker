#!/usr/bin/env python
"""
Test script to check voting and cookie persistence
Run with: python test_voting.py
"""
import os
import django
import requests
from http.cookiejar import CookieJar

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from polls.models import Poll, VoteRecord


if __name__ == "__main__":
    # Test API requests with cookie jar
    session = requests.Session()

    BASE_URL = "http://localhost:8000"

    print("=" * 60)
    print("VOTING COOKIE PERSISTENCE TEST")
    print("=" * 60)

    # Get existing polls
    print("\n1. Fetching existing polls...")
    response = session.get(f"{BASE_URL}/api/polls/")
    print(f"   Status: {response.status_code}")

    # Get first poll
    polls = Poll.objects.all()
    if not polls.exists():
        print("   ERROR: No polls in database!")
        exit(1)

    poll = polls.first()
    print(f"   Found poll: {poll.id} - {poll.question}")

    # Check existing votes
    vote_count = VoteRecord.objects.filter(poll=poll).count()
    print(f"   Existing votes: {vote_count}")
    print(f"   Device tokens: {set(v.device_token_hash[:10] for v in VoteRecord.objects.filter(poll=poll))}")

    print("\n2. Testing first vote...")
    vote_data = {
        "voter_name": "Test User 1",
        "option_ids": [str(poll.options.first().id)]
    }

    response = session.post(
        f"{BASE_URL}/api/polls/{poll.id}/vote/",
        json=vote_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json().get('detail', 'Success')}")
    print(f"   Cookies in session: {dict(session.cookies)}")

    # Check database
    new_vote_count = VoteRecord.objects.filter(poll=poll).count()
    print(f"   New vote count: {new_vote_count}")

    print("\n3. Testing second vote (should be blocked)...")
    vote_data2 = {
        "voter_name": "Test User 2",
        "option_ids": [str(poll.options.first().id)]
    }

    response2 = session.post(
        f"{BASE_URL}/api/polls/{poll.id}/vote/",
        json=vote_data2,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response2.status_code}")
    print(f"   Response: {response2.json().get('detail', 'Unknown')}")

    if response2.status_code == 409:
        print("   ✓ PASSED: Second vote blocked with 409 Conflict")
    else:
        print("   ✗ FAILED: Second vote was not blocked!")

    # Final check
    final_vote_count = VoteRecord.objects.filter(poll=poll).count()
    print(f"   Final vote count: {final_vote_count}")

    print("\n" + "=" * 60)
