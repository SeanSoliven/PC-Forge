
FROM php:8.3-apache

RUN docker-php-ext-install pdo_mysql

RUN a2enmod rewrite headers

RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf

WORKDIR /var/www/html

COPY . /var/www/html/

RUN chown -R www-data:www-data /var/www/html \
    && printf 'DirectoryIndex index.php index.html\n<Directory /var/www/html>\n    AllowOverride All\n    Require all granted\n</Directory>\n' \
    > /etc/apache2/conf-available/pc-forge.conf \
    && a2enconf pc-forge

# Check certificate availability at runtime
RUN printf '#!/bin/sh\nif [ -r /etc/secrets/ca.pem ]; then\n  echo "Aiven CA certificate is readable"\nelse\n  echo "WARNING: Aiven CA certificate is missing or unreadable"\nfi\nexec apache2-foreground\n' > /usr/local/bin/start-pc-forge \
    && chmod +x /usr/local/bin/start-pc-forge

EXPOSE 80

CMD ["start-pc-forge"]
