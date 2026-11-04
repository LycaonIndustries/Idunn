/**
 * Test environment initialization for frontend component tests.
 */
import { GlobalRegistrator } from '@happy-dom/global-registrator';
import { beforeEach } from 'bun:test';
// Register mock browser DOM objects globally so React testing library can mount components.
GlobalRegistrator.register();
// Clear document body between tests so previous renders do not leak into subsequent assertions.
beforeEach(() => {
    document.body.innerHTML = '';
});
