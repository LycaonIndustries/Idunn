import { useContext } from 'react'
import { MultiCookContext } from './multiCookContextDef'

export function useMultiCook() {
  return useContext(MultiCookContext)
}
