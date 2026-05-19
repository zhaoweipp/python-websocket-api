import io from 'socket.io-client'

const socket = io('http://127.0.0.1:8000', {
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  timeout: 10000,
})

socket.on('connect', () => {
  console.log('engine.io sid:', socket.id)
})

socket.on('serial:data', (payload) => {
  console.log('serial bytes:', payload)
})

export function sendSerial(data) {
  socket.emit('serial:write', data, (ack) => {
    console.log('ack:', ack)
  })
}
