# Cloud Architecture Design - Survey System

We will now design the cloud-deployed systems structure for an hypothetical case in which we have a high stream of surveys submissions per minute, wth results available for analytics within seconds of submission. The case presented here will be rather rather simple, but we will discuss the decisions made, benefits and tradeoffs.

## Cloud Pipeline Architecture

The following solution is splitted in 6 stages:

Survey Frontend --> API Load --> Message Queue --> Stream Processor --> Storage DB --> Analytics Presentation

### 1. Survey Frontend

This will be the survey form, deployed in a simple frontend application. For the sake of simplicity we will assume that no 3rd party login or registering is necessary for submitting the survey. All the fields will be filled by the user. This frontend will contain some sanitization conditions in each of the fields, but this can be double checked from the API side as well.

### 2. API Load

Submissions are sent by the user from the frontend to a RESTful API or handled directly by cloud services like API Management (Azure) or AWS API Gateway, before being forwarded to the message queue. This layer can provide authentication (only legitimate users submit surveys), extra input validation, rate limiting to prevent DDoS attacks on the survey, and it also enforces HTTPS. Without it the pipeline would be extra vulnerable to invalid data or malicious traffic.

### 3. Message Queue

Message queues (such as Apache Kafka) enable events from the API to be buffered and processed by the next service at its own rate. But it allows us to handle sudden spikes of traffic at a steady rate and handle failures more gracefully (if the stream processor shuts down, the queue will still build up events until it is available again, instead of completely loosing that data). This makes the pipeline stable: you don’t lose data, don’t overload processors, and processing speed remains consistent.

### 4. Stream Processor

This service will consume the queue. At this stage it performs schema validation, transformation, and basic cleaning in-flight (the sort of operations we did in `data_sanitization.py`). It also can push malformed records to a Dead Letter Queue (DLQ) for later inspection. For our case (basic sanitization + ~1.000 events/min) using simple services like Azure Functions or AWS for this operation might be enough. But for larger operations, aggregates and higher througphut other services like Azure Stream should be considered.

### 5. Storage DB

The processed, cleaned surveys are loaded into an analytics-optimized database. Columnar databases are perfect for this such as Redshift or Azure Synapse Analytics. These databases are specifically designed to handle large volumes of structured data and to support complex queries, aggregations, and reporting tasks with minimal delay.

### 6. Analytics Presentation

Analytics results can be presented via a custom made dashboards frontend, or directly with tools like Power BI.

## Extras & Future Considerations

### Security

- Implement end-to-end encryption for data in transit and at rest to protect sensitive survey information.
- Use role-based access control (RBAC) and least privilege principles for all services and data stores.
- Regularly audit API endpoints and message queues for vulnerabilities and apply security patches promptly.
- Enable logging and monitoring for suspicious activity and errors (such as Azure Monitor, external log analytics tools, etc).

### Scalability

- Design each stage of the pipeline to scale independently, using auto-scaling features in cloud services (e.g., Azure Functions, managed Kafka, Synapse Analytics).
- Employ partitioning and sharding strategies in message queues and databases to handle high throughput and large datasets.
- Use load balancers and distributed architectures to prevent bottlenecks and ensure high availability.
- Continuously monitor performance metrics and adjust resource allocation to meet demand spikes efficiently.
