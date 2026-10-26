
FROM php:8.3-apache

RUN docker-php-ext-install pdo_mysql

RUN a2enmod rewrite headers proxy proxy_http auth_basic authn_file \
    && groupadd --system pc-training \
    && useradd --system --gid pc-training --no-create-home --shell /usr/sbin/nologin pc-training

RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf

WORKDIR /var/www/html

COPY . /var/www/html/

RUN chown -R root:www-data /var/www/html \
    && find /var/www/html -type d -exec chmod 750 {} + \
    && find /var/www/html -type f -exec chmod 640 {} + \
    && printf 'DirectoryIndex index.php index.html\n<Directory /var/www/html>\n    AllowOverride All\n    Require all granted\n</Directory>\n' \
    > /etc/apache2/conf-available/pc-forge.conf \
    && a2enconf pc-forge

COPY docker/start-pc-forge /usr/local/bin/start-pc-forge
COPY docker/production.ini /usr/local/etc/php/conf.d/zz-production.ini
COPY training-src/public/ /opt/pc-forge-training/
COPY assets/style.css /opt/pc-forge-training/assets/style.css
COPY docker/prepare-training.php /usr/local/lib/pc-forge/prepare-training.php
COPY docker/training-config.php /usr/local/lib/pc-forge/training-config.php
COPY docker/training-router.php /usr/local/lib/pc-forge/training-router.php
COPY docker/verify-training.php /usr/local/lib/pc-forge/verify-training.php
COPY docker/supervise-pc-forge /usr/local/bin/supervise-pc-forge
RUN chown -R root:pc-training /opt/pc-forge-training \
    && find /opt/pc-forge-training -type d -exec chmod 750 {} + \
    && find /opt/pc-forge-training -type f -exec chmod 640 {} + \
    && chown -R root:root /usr/local/lib/pc-forge \
    && chmod 755 /usr/local/lib/pc-forge /usr/local/lib/pc-forge/*.php \
    && sed -i 's/\r$//' /usr/local/bin/supervise-pc-forge \
    && chmod 755 /usr/local/bin/supervise-pc-forge
RUN sed -i 's/\r$//' /usr/local/bin/start-pc-forge \
    && chmod 755 /usr/local/bin/start-pc-forge

EXPOSE 80

# PID 1 is our supervisor, not Apache. Override the base image's SIGWINCH.
STOPSIGNAL SIGTERM

CMD ["start-pc-forge"]
