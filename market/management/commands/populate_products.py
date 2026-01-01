from django.core.management.base import BaseCommand
from market.models import Product


class Command(BaseCommand):
    help = 'Populate initial products for the Village Artisan Market'

    def handle(self, *args, **options):
        products_data = [
            {
                "name": "Handwoven Bamboo Basket",
                "price": 850,
                "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQElLboj8ry3YOE-lAOfTcajrrBXEA7mh0n-A&s"
            },
            {
                "name": "Terracotta Handcrafted Necklace",
                "price": 650,
                "img": "https://soul-india.in/cdn/shop/files/3951073353.jpg?v=1716037171&width=1200"
            },
            {
                "name": "Coconut Shell Bowl Set",
                "price": 1200,
                "img": "https://ambihome.in/cdn/shop/files/PRRM1475.jpg?v=1747895368&width=3899"
            },
            {
                "name": "Handmade Jute Bag",
                "price": 950,
                "img": "https://5.imimg.com/data5/SELLER/Default/2025/3/495234873/BX/KD/HI/40222619/jute-carry-bag.jpg"
            },
            {
                "name": "Woolen Handmade Socks",
                "price": 450,
                "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSntv_aZg0bT508UrhxoTjq6eiT81CZ8Mudow&s"
            },
            {
                "name": "Clay Water Pot",
                "price": 700,
                "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTGVSucJ33ZO-7VGrZ-PUHOXztbFZX42Hi3HQ&s"
            },
            {
                "name": "Wooden Spice Box",
                "price": 1100,
                "img": "https://ii1.pepperfry.com/media/catalog/product/d/u/1100x1210/dudki-handmade-mango-wooden-spice-box-for-kitchen-for-kitchen-with-8-small-partitions-and-transparen-dgznxj.jpg"
            },
            {
                "name": "Handloom Cotton Shawl",
                "price": 1600,
                "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqguUcl70M6SwqbXGWdY2CrStRuULLrQBZHA&s"
            }
        ]

        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data["name"],
                defaults={
                    "price": product_data["price"],
                    "img": product_data["img"]
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created product: {product.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Product already exists: {product.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully populated {created_count} new products. '
                f'Total products: {Product.objects.count()}'
            )
        )



