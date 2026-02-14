# Frontend

Frontend for Northwind Commerce Knowledge Assistant.

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

## Development

### Linting and Formatting

```bash
# Run ESLint
npm run lint

# Auto-fix linting issues
npm run lint:fix

# Check formatting
npm run format:check

# Format code
npm run format
```

### Type Checking

```bash
# Run TypeScript type checking
npm run type-check
```

### Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Building

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/            # Source files
├── public/         # Static assets
├── .eslintrc.json  # ESLint configuration
├── .prettierrc.json # Prettier configuration
├── tsconfig.json   # TypeScript configuration
├── package.json    # Dependencies and scripts
└── README.md       # This file
```

## Configuration

- **Node Version**: 20
- **Build Tool**: Vite
- **Framework**: React (when added)
- **Language**: TypeScript
- **Linter**: ESLint with TypeScript support
- **Formatter**: Prettier
- **Test Framework**: Vitest

## CI/CD

See [../.github/workflows/frontend.yml](../.github/workflows/frontend.yml) for CI configuration.