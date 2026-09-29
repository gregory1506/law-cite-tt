import { mount } from 'svelte'
import '@fontsource-variable/inter'
import '@fontsource-variable/source-serif-4'
import './styles/tokens.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app'),
})

export default app
