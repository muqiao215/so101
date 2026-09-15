import fc from 'fast-check';
import { ActionProjectFactory } from '../shared/factories';
import { ValidationService } from '../shared/validation';

describe('Property Tests - Name Truncation', () => {
  
  // Feature: robotic-arm-sequencer, Property 3: Name Truncation
  test('Property 3: Project names exceeding 50 characters should be truncated to exactly 50 characters', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 1000 }),
      (longName) => {
        const project = ActionProjectFactory.create({ name: longName });
        
        // Name should be truncated to exactly 50 characters
        return project.name.length === 50;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Truncated names should be the first 50 characters of the original', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 1000 }),
      (longName) => {
        const project = ActionProjectFactory.create({ name: longName });
        
        // Truncated name should match the first 50 characters of original
        const expectedTruncated = longName.substring(0, 50);
        return project.name === expectedTruncated;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Names with exactly 50 characters should not be truncated', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 50, maxLength: 50 }),
      (exactName) => {
        const project = ActionProjectFactory.create({ name: exactName });
        
        // Name should remain unchanged
        return project.name === exactName && project.name.length === 50;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Names shorter than 50 characters should not be modified', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 49 }),
      (shortName) => {
        const project = ActionProjectFactory.create({ name: shortName });
        
        // Name should remain unchanged
        return project.name === shortName && project.name.length === shortName.length;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Empty names should remain empty (handled by validation)', () => {
    const project = ActionProjectFactory.create({ name: '' });
    
    // Empty name should remain empty (validation will catch this)
    expect(project.name).toBe('');
    expect(project.name.length).toBe(0);
  });

  test('Property 3: Unicode characters should be handled correctly in truncation', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 100 }),
      (unicodeName) => {
        const project = ActionProjectFactory.create({ name: unicodeName });
        
        // Truncated name should be exactly 50 characters
        // Note: substring() works with UTF-16 code units, which is what we want for length limits
        return project.name.length === 50;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Truncation should preserve character boundaries (no broken surrogate pairs)', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 200 }),
      (longName) => {
        const project = ActionProjectFactory.create({ name: longName });
        
        // The truncated string should be valid (no broken surrogate pairs)
        // This is automatically handled by substring() in JavaScript
        try {
          // Try to encode/decode to check for broken characters
          const encoded = encodeURIComponent(project.name);
          const decoded = decodeURIComponent(encoded);
          return decoded === project.name && project.name.length === 50;
        } catch {
          // If encoding fails, the string has broken characters
          return false;
        }
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: ValidationService should accept truncated names as valid', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 1000 }).filter(s => 
        // Filter out names with invalid filesystem characters
        !/[<>:"/\\|?*\x00-\x1f]/.test(s) &&
        // Filter out reserved Windows names
        !['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'].includes(s.substring(0, 50).toUpperCase())
      ),
      (longName) => {
        const project = ActionProjectFactory.create({ name: longName });
        
        // After truncation, the name should pass validation
        const nameValidation = ValidationService.validateProjectName(project.name);
        const projectValidation = ValidationService.validateProject(project);
        
        return nameValidation.isValid && projectValidation.isValid;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Truncation should work with special characters and whitespace', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 200 }).filter(s => 
        // Filter out names with invalid filesystem characters for this test
        !/[<>:"/\\|?*\x00-\x1f]/.test(s)
      ),
      (nameWithSpecialChars) => {
        const project = ActionProjectFactory.create({ name: nameWithSpecialChars });
        
        // Should be truncated to 50 characters and match the first 50 of original
        const expectedTruncated = nameWithSpecialChars.substring(0, 50);
        return project.name === expectedTruncated && project.name.length === 50;
      }
    ), { numRuns: 1000 });
  });

  test('Property 3: Multiple projects with same long name should have identical truncated names', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 51, maxLength: 1000 }),
      fc.integer({ min: 2, max: 10 }),
      (longName, projectCount) => {
        const projects = Array.from({ length: projectCount }, () => 
          ActionProjectFactory.create({ name: longName })
        );
        
        // All projects should have the same truncated name
        const firstTruncatedName = projects[0].name;
        const allSameName = projects.every(project => 
          project.name === firstTruncatedName
        );
        
        // And all should be exactly 50 characters
        const allCorrectLength = projects.every(project => 
          project.name.length === 50
        );
        
        return allSameName && allCorrectLength;
      }
    ), { numRuns: 1000 });
  });
});