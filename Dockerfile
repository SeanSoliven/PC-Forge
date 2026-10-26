
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

COPY docker/start-pc-forge /usr/local/bin/start-pc-forge
COPY docker/production.ini /usr/local/etc/php/conf.d/zz-production.ini
RUN sed -i 's/\r$//' /usr/local/bin/start-pc-forge \
    && chmod 755 /usr/local/bin/start-pc-forge

EXPOSE 80

CMD ["start-pc-forge"]
