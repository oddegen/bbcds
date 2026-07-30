import { render, screen } from '@testing-library/react'

import App from './App'

describe('App', () => {
  it('renders a plain hello screen', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Hello' })).toBeInTheDocument()
  })
})
