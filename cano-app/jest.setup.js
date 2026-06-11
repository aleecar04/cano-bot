// Mock global de los iconos para evitar warnings sobre nombres de iconos
// no válidos y actualizaciones internas de <Icon> fuera de act().
jest.mock('@expo/vector-icons', () => {
  const React = jest.requireActual('react');
  const { Text } = jest.requireActual('react-native');
  const makeIcon = () => (props) => React.createElement(Text, props, null);
  return new Proxy({}, { get: makeIcon });
});
