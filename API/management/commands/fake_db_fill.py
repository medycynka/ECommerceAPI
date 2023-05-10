from django.core.management.base import BaseCommand


from API import factories


class Command(BaseCommand):
    help = "Create fake db data for testing"
    requires_system_checks = ()
    skip_checks = True

    def add_arguments(self, parser):
        parser.add_argument('batch_size', nargs=1, type=int,
                            help="Number of record to generate for each model to create")
        parser.add_argument('-u', '--users', action='store_true', default=False,
                            help="Create user models")
        parser.add_argument('-cat', '--categories', action='store_true', default=False, help="Create Category models")
        parser.add_argument('-p', '--products', action='store_true', default=False, help="Create Product models")
        parser.add_argument('-a', '--addresses', action='store_true', default=False, help="Create Address models")
        parser.add_argument('-o', '--orders', action='store_true', default=False, help="Create Order models")

    def handle(self, *args, **options):
        batch_size = int(options['batch_size'][0])
        created_anything = False

        if options['users']:
            self.stdout.write(self.style.SUCCESS(f'Generating {batch_size} test users...'))
            factories.UserFactory.create_batch(batch_size)
            self.stdout.write(self.style.SUCCESS(
                f'Successfully created {batch_size} test users.'
            ))
            created_anything = True

        if options['categories']:
            self.stdout.write(self.style.SUCCESS(f'Generating {batch_size} test categories...'))
            factories.CategoryFactory.create_batch(batch_size)
            self.stdout.write(self.style.SUCCESS(f'Successfully created {batch_size} test categories.'))
            created_anything = True

        if options['products']:
            self.stdout.write(self.style.SUCCESS(f'Generating {batch_size} test products...'))
            factories.ProductFactory.create_batch(batch_size)
            self.stdout.write(self.style.SUCCESS(f'Successfully created {batch_size} test products.'))
            created_anything = True

        if options['addresses']:
            self.stdout.write(self.style.SUCCESS(f'Generating {batch_size} test addresses...'))
            factories.AddressFactory.create_batch(batch_size)
            self.stdout.write(self.style.SUCCESS(f'Successfully created {batch_size} test addresses.'))
            created_anything = True

        if options['orders']:
            self.stdout.write(self.style.SUCCESS(f'Generating {batch_size} test orders...'))
            factories.OrderFactory.create_batch(batch_size)
            self.stdout.write(self.style.SUCCESS(f'Successfully created {batch_size} test orders.'))
            created_anything = True

        if created_anything:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created all test data.\n'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nNothing has been created. Use at least one option (-u, -c, -p, -a or -o) '
                                   f'to create test models. See --help for more info.\n')
            )
