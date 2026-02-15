FROM nginx:1.25-alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create html directory
RUN mkdir -p /usr/share/nginx/html

# Add a simple index page
RUN echo '<html><body><h1>Night-Feed Podcast</h1><p>RSS Feed: <a href="/feed.xml">feed.xml</a></p></body></html>' > /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
