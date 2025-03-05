# Welcome to the Seed monorepo !

Below is an overview of how we work in the Seed tech team.

## 1. Overview of Development at Seed

All the code for Seed lives in this **monorepo**.

Using a monorepo allows us to:


- Maintain consistency across dependencies.
- Streamline collaboration between teams.
- Simplify tooling and versioning.
- Scale development with ease.

The **Seed stack** leverages **TypeScript** across the board, ensuring end-to-end type safety and a seamless developer experience.

### The Stack:

- **Back-End**: [Node.js](https://nodejs.org/) with [Express](https://expressjs.com/) and [tRPC](https://trpc.io) for APIs.
- **Front-End**: [React](https://react.dev/) with [Vite](https://vitejs.dev/) for lightning-fast development.
- **Database**: [Firebase](https://firebase.google.com/) for real-time synchronization, authentication, and storage.
- **Caching**: [Redis](https://redis.io/) for rate-limiting and performance optimization.
- **Error Tracking**: [Sentry](https://sentry.io) to monitor and resolve issues quickly.
- **Testing**: [Vitest](https://vitest.io) for robust unit and integration testing.

---

### Noteworthy Directories:

- **`packages/apps/frontend`**: The front-end application.
- **`packages/apps/backend`**: The back-end services.
- **`packages/apps/api-challenge`**: The API challenge.
- **`packages/apps/api-scoring`**: The API scoring.
- **`packages/apps/web-site`**: The web site.
- **`packages/libs`**: Shared libraries and tools for both front-end and back-end.
- **`tools/`**: Development scripts for automation and efficiency.

By combining cutting-edge technologies and a monorepo architecture, Seed ensures high performance, maintainability, and seamless collaboration between components.

---

## 2. Technologies Used

### **Front-End**

- **Frameworks & Libraries**:

  - Built with **Vite.js** for efficient, fast builds.
  - Used **TanStack Router** for client-side routing.
  - Managed server state with **TanStack Query**.
  - Developed APIs with **tRPC** for end-to-end type safety.
  - Styled user interfaces using **TailwindCSS**.

- **Key Features**:
  - Modular architecture managed with **TurboRepo**.
  - Custom reusable packages to enhance productivity.
  - Seamlessly deployed on **Vercel** for production-ready performance.

---

### **Back-End**

- **Frameworks & Tools**:

  - Scalable services built with **Node.js**, **Express**, and **tRPC**.
  - **Firebase** for:
    - Authentication and secure access.
    - Real-time data synchronization.
    - Data storage solutions.

- **Key Features**:
  - RESTful APIs and **tRPC** endpoints for efficient front-end communication.
  - Scalable architecture optimized for multiple environments.
  - Environment-specific configurations for streamlined deployment.

---

### **Other Responsibilities**

- **Monorepo Management**:

  - Single **TurboRepo**-managed codebase for consistent practices.
  - Shared libraries for code reuse across applications.

- **Collaboration**:

  - Worked with cross-functional teams to define and deliver features effectively.
  - Established best practices through code reviews for maintainable and scalable solutions.

- **CI/CD Pipelines**:
  - Automated deployments and testing pipelines for reliable delivery.

---

## 3. Key Features

1. **End-to-End Type Safety**:

   - Complete **TypeScript** implementation across the stack.

2. **Real-Time Capabilities**:

   - Leveraged Firebase for live updates and synchronization.

3. **Scalability**:

   - Designed systems to handle growth seamlessly.

4. **Error Monitoring**:

   - Integrated **Sentry** for comprehensive error tracking and resolution.

5. **Automated Deployments**:
   - Built CI/CD pipelines for rapid and reliable shipping.

---

## **Installation & Setup**

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install dependencies:

   ```bash
   yarn install
   ```

3. Start the development server:

   ```bash
   yarn dev
   ```

   - For run specific package:

     ```bash
     yarn workspace <package-name> dev
     ```

     example:

     ```bash
       yarn dev --workspace=frontend
     ```

---

## **Contributors**

1. Create a new branch:

   ```bash
   git checkout -b <branch-name>
   ```

2. Make your changes and commit them:

   ```bash
    git add .
    git commit -m "Your commit message"
   ```

3. Push to the original branch:

   ```bash
   git push origin <branch-name>
   ```

4. Create a pull request in the original repository.
# ssedtech
# seedtech
