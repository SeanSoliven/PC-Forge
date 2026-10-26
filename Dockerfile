
FROM php:8.3-apache

RUN docker-php-ext-install pdo_mysql

RUN a2enmod rewrite headers

WORKDIR /var/www/html

COPY . /var/www/html/

RUN chown -R www-data:www-data /var/www/html \
    && printf 'DirectoryIndex index.php index.html\n<Directory /var/www/html>\n    AllowOverride All\n    Require all granted\n</Directory>\n' \
    > /etc/apache2/conf-available/pc-forge.conf \
    && a2enconf pc-forge

EXPOSE 80

CMD ["apache2-foreground"]
