# Technical Design Document: Car Park Management System

## Architecture Overview

The Car Park Management System (CPMS) is a client-server architecture designed to handle vehicle entry, exit, parking spot allocation, and reporting. The architecture includes a client, server, database, and various components to ensure robust functionality and security.

### Components

1. **Client (User Interface)**
   - **Frontend**: Web-based interface for users to register, enter/exit the car park, and view available parking spots.
   - **Responsibilities**: Handle user interactions, communicate with the server, and display data.

2. **Server (Application Logic)**
   - **Backend**: Python-based server using Flask or Django for handling requests and business logic.
   - **Responsibilities**: Manage user authentication, interact with the database, and provide APIs for client communication.

3. **Database (Data Storage)**
   - **Database Management System**: PostgreSQL or MySQL for storing user data, parking spot information, and transaction records.
   - **Responsibilities**: Persist data, ensure data integrity, and support efficient querying.

4. **API/Interface**
   - **RESTful API**: Define RESTful endpoints for user registration, vehicle entry/exits, parking spot management, and reporting.
   - **GraphQL API**: Provide an alternative for more complex queries and mutations.

5. **Authentication and Authorization**
   - **Authentication**: OAuth2/OpenID Connect for secure user authentication.
   - **Authorization**: Role-based access control (RBAC) to manage user permissions.

6. **Notifications**
   - **Email/SMS Service**: Integration with email and SMS services for sending notifications to users.
   - **Responsibilities**: Send reminders, updates, and alerts.

7. **Monitoring and Logging**
   - **Logging Framework**: Python’s logging module or ELK Stack for centralized logging.
   - **Monitoring Tools**: Prometheus and Grafana for monitoring system performance and health.

8. **Security**
   - **Encryption**: Data encryption in transit and at rest.
   - **Security Headers**: Implement security headers for HTTP requests.

### Data Model

#### Database Schema

- **Users Table**
  - `user_id` (Primary Key)
  - `username`
  - `email`
  - `password_hash`
  - `role` (e.g., staff, user)

- **Parking Spots Table**
  - `spot_id` (Primary Key)
  - `spot_number`
  - `status` (e.g., occupied, available)
  - `allocated_to` (Foreign Key to Users)

- **Transactions Table**
  - `transaction_id` (Primary Key)
  - `user_id` (Foreign Key to Users)
  - `spot_id` (Foreign Key to Parking Spots)
  - `entry_time`
  - `exit_time`
  - `duration`
  - `amount`

#### API Endpoints

- **User Registration**
  - **Endpoint**: `/register`
  - **Method**: POST
  - **Payload**: `{ username: string, email: string, password: string }`
  - **Response**: `{ success: boolean, message: string }`

- **User Login**
  - **Endpoint**: `/login`
  - **Method**: POST
  - **Payload**: `{ username: string, password: string }`
  - **Response**: `{ success: boolean, token: string, message: string }`

- **Vehicle Entry**
  - **Endpoint**: `/entry`
  - **Method**: POST
  - **Payload**: `{ user_id: string, spot_id: string, entry_time: datetime }`
  - **Response**: `{ success: boolean, message: string }`

- **Vehicle Exit**
  - **Endpoint**: `/exit`
  - **Method**: POST
  - **Payload**: `{ transaction_id: string, exit_time: datetime }`
  - **Response**: `{ success: boolean, message: string, amount: float }`

- **View Parking Spots**
  - **Endpoint**: `/spots`
  - **Method**: GET
  - **Response**: `[ { spot_id: string, spot_number: string, status: string } ]`

- **Generate Reports**
  - **Endpoint**: `/reports`
  - **Method**: GET
  - **Params**: `start_date`, `end_date`
  - **Response**: `{ usage: int, revenue: float, trends: [ { date: string, usage: int } ] }`

### Error Handling

- **Validation Errors**: Return 400 status code with error messages for invalid inputs.
- **Authentication Errors**: Return 401 status code for unauthorized access.
- **Authorization Errors**: Return 403 status code for forbidden actions.
- **Database Errors**: Return 500 status code with error messages for database issues.
- **External Service Errors**: Return 502 status code for service unavailable.

### Security Considerations

- **Data Encryption**: Use HTTPS for all data in transit and encrypt sensitive data stored in the database.
- **Input Validation**: Validate all inputs to prevent SQL injection, XSS, and other attacks.
- **Authentication**: Use OAuth2/OpenID Connect for secure authentication.
- **Authorization**: Implement role-based access control to restrict access to sensitive endpoints.
- **Monitoring and Logging**: Use ELK Stack for centralized monitoring and logging.
- **Regular Updates**: Keep all dependencies and libraries updated to patch security vulnerabilities.

### Dependencies

- **Backend**: Flask or Django, PostgreSQL/MySQL, Python’s logging module, OAuth2/OpenID Connect library, ELK Stack
- **Frontend**: HTML/CSS/JavaScript, Bootstrap, Fetch API
- **Notifications**: Python’s smtplib or Twilio for email/SMS notifications
- **Monitoring**: Prometheus, Grafana

### Alternatives

- **Database**: Consider using a NoSQL database like MongoDB if the system needs to scale horizontally and handle unstructured data.
- **API**: Consider using GraphQL for more complex queries and mutations if the system has a lot of data and complex relationships.
- **Notifications**: Consider integrating with Twilio for SMS notifications or AWS SNS for email notifications.
- **Monitoring**: Consider using Prometheus and Grafana for more advanced monitoring and alerting capabilities.

## Conclusion

The Car Park Management System is designed to be scalable, secure, and user-friendly. By following this technical design, the system will provide a robust platform for managing car parks and improving the overall user experience.