# Generated migration to fix device vote constraint
# Prevents multiple votes from same device on same poll (regardless of option)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0004_poll_expired_notified_at_rename_vote_and_more'),
    ]

    operations = [
        # Remove the incorrect constraint that allows voting for different options
        migrations.RemoveConstraint(
            model_name='voterecord',
            name='unique_option_vote_per_device',
        ),
        # Add correct constraint: one vote per device per poll
        migrations.AddConstraint(
            model_name='voterecord',
            constraint=models.UniqueConstraint(
                fields=('poll', 'device_token_hash'),
                name='unique_vote_per_device_per_poll',
            ),
        ),
    ]
