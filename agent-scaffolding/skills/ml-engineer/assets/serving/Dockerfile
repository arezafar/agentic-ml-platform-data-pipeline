# =============================================================================
# MOJO Serving Container
# =============================================================================
# Lightweight container for low-latency model inference
# Uses h2o-genmodel.jar to score predictions without full H2O cluster
#
# Build: docker build -t mojo-serving .
# Run:   docker run -p 8080:8080 -v ./models:/models mojo-serving
# =============================================================================

FROM amazoncorretto:17-alpine

LABEL maintainer="ml-engineer-agent"
LABEL description="H2O MOJO Serving Container for Production Inference"

WORKDIR /app

# Install curl for healthchecks
RUN apk add --no-cache curl

# Copy the Spring Boot wrapper application
# (In production, this would be built separately)
COPY app.jar /app/model-serving.jar

# Create model directory
RUN mkdir -p /models/production

# Expose REST API port
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the serving application
ENTRYPOINT ["java", "-Xmx1g", "-jar", "model-serving.jar"]
